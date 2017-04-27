#!/usr/bin/env python3
import asyncio
import importlib
import logging
import os
import smtplib
from email import message_from_bytes
from email.policy import EmailPolicy

import aiomonitor
from aiosmtpd.smtp import SMTP
from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Proxy, CRLF, NLCRE

from mail2alert import plugin
from mail2alert.config import Configuration

"""
This is a mail proxy server based on Python 3 standard smtpd.PureProxy.
By default, mail sent to it will be forwarded to a downstream mail server.

Managers are plugged into the workflow to read each message and possibly
act on it. If it wants the message, they will provide (potentially) new
values for sender, recipient and data.
If the recipient list ends up empty, the message will not be sent by the
email proxy. This means that the manager can drop messages or transport
them with other mechanisms than email.
"""


def update_mail_to_from(bytes_data, rcpttos, mailfrom):
    msg = message_from_bytes(bytes_data, policy=EmailPolicy(utf8=True, linesep='\r\n'))

    logging.debug('Removing To: %s', msg['To'])
    del msg['To']
    msg['To'] = rcpttos
    logging.debug('Added To: %s', msg['To'])

    logging.debug('Removing From: %s', msg['From'])
    del msg['From']
    msg['From'] = mailfrom
    logging.debug('Added From: %s', msg['From'])

    mail_bytes = msg.as_bytes()
    logging.debug(
        'update_mail_to_from got %i bytes and returned %i bytes',
        len(bytes_data),
        len(mail_bytes)
    )
    return mail_bytes


class SMTPUTF8Controller(Controller):
    def factory(self):
        return  SMTP(self.handler, enable_SMTPUTF8=True)


class Mail2AlertProxy(Proxy):
    def __init__(self, host, port, managers):
        self.mail2alert_managers = managers
        super().__init__(host, port)

    async def handle_DATA(self, server, session, envelope):
        """
        The Proxy class had confused strings and bytes!
        """
        logging.debug('handle_DATA got %s', envelope.content.decode('utf-8'))
        lines = envelope.content.splitlines(keepends=True)
        # Look for the last header
        i = 0
        ending = CRLF
        for line in lines:  # pragma: nobranch
            if NLCRE.match(line.decode('utf-8')):
                ending = line
                break
            i += 1
        lines.insert(i, b'X-Peer: %s%s' % (session.peer[0].encode('utf-8'), ending))
        data = b''.join(lines)
        refused = self._deliver(envelope.mail_from, envelope.rcpt_tos, data)
        if refused:
            logging.info('we got some refusals: %s' % refused)
        return '250 OK'

    def _deliver(self, mailfrom, rcpttos, data):
        for manager in self.mail2alert_managers:
            if manager.wants_message(mailfrom, rcpttos, data):
                mailfrom, rcpttos, data = manager.process_message(mailfrom, rcpttos, data)
                if rcpttos:
                    data = update_mail_to_from(data, rcpttos, mailfrom)
                break
        if rcpttos:
            # return super()._deliver(mailfrom, rcpttos, data)
            logging.info('Sending mail to %s', rcpttos)
            return self.fixed_base_deliver(mailfrom, rcpttos, data)
        else:
            logging.info('Dropping email.')
            return rcpttos

    def fixed_base_deliver(self, mail_from, rcpt_tos, data):
        """
        Bug in log.exception in Proxy._deliver
        """
        refused = {}
        try:
            s = smtplib.SMTP()
            s.connect(self._hostname, self._port)
            try:
                logging.debug(
                    'smtplib.SMTP().sendmail(%s, %s, data) with...',
                    mail_from,
                    rcpt_tos
                )
                logging.debug('Data = %r', data)
                refused = s.sendmail(mail_from, rcpt_tos, data)
            finally:
                s.quit()
        except smtplib.SMTPRecipientsRefused as e:
            logging.info('got SMTPRecipientsRefused')
            refused = e.recipients
        except (OSError, smtplib.SMTPException) as e:
            logging.exception('got %s', e.__class__)  # We were missing %s!!!
            # All recipients were refused.  If the exception had an associated
            # error code, use it.  Otherwise, fake it with a non-triggering
            # exception code.
            errcode = getattr(e, 'smtp_code', -1)
            errmsg = getattr(e, 'smtp_error', 'ignore')
            for r in rcpt_tos:
                refused[r] = (errcode, errmsg)
        return refused


def host_port(text, default_port=25):
    if ':' in text:
        host, port = text.split(':')
        return host, int(port)
    else:
        return text, default_port


async def proxy_mail():
    cnf = Configuration()
    local_host, local_port = host_port(cnf['local-smtp'])
    remote_host, remote_port = host_port(cnf['remote-smtp'])
    managers = []
    for manager in cnf['managers']:
        manager_module = importlib.import_module('.' + manager['name'], plugin.__name__)
        managers.append(
            manager_module.Manager(manager)
        )
    cont = SMTPUTF8Controller(
        Mail2AlertProxy(remote_host, remote_port, managers),
        hostname=local_host,
        port=local_port)
    cont.start()


def get_loglevel(env=os.environ):
    log_env = env.get('LOGLEVEL')
    return logging._nameToLevel.get(log_env, logging.INFO)


def main(loglevel=None):
    if loglevel is None:
        loglevel = get_loglevel()
    logging.basicConfig(
        format="%(asctime)s:%(levelname)s:%(name)s:%(message)s",
        level=loglevel
    )
    loop = asyncio.get_event_loop()
    loop.create_task(proxy_mail())
    try:
        with aiomonitor.start_monitor(loop=loop):
            logging.info("Now you can connect with: nc localhost 50101")
            loop.run_forever()
    except KeyboardInterrupt:
        logging.info('Got KeyboardInterrupt')
