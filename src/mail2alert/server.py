#!/usr/bin/env python3
import asyncio
import importlib
import logging
import smtplib
from email import message_from_bytes
from email.policy import EmailPolicy

import aiomonitor
from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Proxy, CRLF, NLCRE

from mail2alert import plugin
from mail2alert.config import Configuration

"""
This is a mail proxy server based on Python 3 standard smtpd.PureProxy.
By default, mail sent to it will be forwarded to a downstream mail server.

A manager (potentially more than one) is plugged into the workflow to
read each message and possibly act on it. If it wants the message, it
    will provide (potentially) new values for sender, recipient and data.
If the recipient list is empty, the message will not be sent by the email
proxy. This means that the manager can drop messages or transport then
with other mechanisms than email.
"""


def update_mail_to_from(bytes_data, rcpttos, mailfrom):
    msg = message_from_bytes(bytes_data, policy=EmailPolicy())
    del msg['To']
    msg['To'] = rcpttos
    del msg['From']
    msg['From'] = mailfrom
    return msg.as_bytes()


class Mail2AlertProxy(Proxy):
    def __init__(self, host, port, managers):
        self.mail2alert_managers = managers
        super().__init__(host, port)

    async def handle_DATA(self, server, session, envelope):
        """
        The Proxy class had confused strings and bytes!
        """
        lines = envelope.content.splitlines(keepends=True)
        # Look for the last header
        i = 0
        ending = CRLF
        for line in lines:  # pragma: nobranch
            if NLCRE.match(line.decode('ascii')):
                ending = line
                break
            i += 1
        lines.insert(i, b'X-Peer: %s%s' % (session.peer[0].encode('ascii'), ending))
        data = b''.join(lines)
        refused = self._deliver(envelope.mail_from, envelope.rcpt_tos, data)
        if refused:
            logging.info('we got some refusals: %s' % refused)
        return '250 OK'

    def _deliver(self, mailfrom, rcpttos, data):
        for manager in self.mail2alert_managers:
            if manager.wants_message(mailfrom, rcpttos, data):
                mailfrom, rcpttos, data = manager.process_message(mailfrom, rcpttos, data)
                break
        if rcpttos:
            data = update_mail_to_from(data, rcpttos, mailfrom)
            #return super()._deliver(mailfrom, rcpttos, data)
            return self.fixed_base_deliver(mailfrom, rcpttos, data)
        else:
            logging.info('Dropping email.')

    def fixed_base_deliver(self, mail_from, rcpt_tos, data):
        """
        Bug in log.exception in Proxy._deliver
        """
        refused = {}
        try:
            s = smtplib.SMTP()
            s.connect(self._hostname, self._port)
            try:
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


async def proxy_mail(loop):
    cnf = Configuration()
    local_host, local_port = host_port(cnf['local-smtp'])
    remote_host, remote_port = host_port(cnf['remote-smtp'])
    managers = []
    for manager in cnf['managers']:
        manager_module = importlib.import_module('.' + manager['name'], plugin.__name__)
        managers.append(
            manager_module.Manager(manager)
        )
    cont = Controller(
        Mail2AlertProxy(remote_host, remote_port, managers),
        hostname=local_host,
        port=local_port)
    cont.start()


def main(loglevel=logging.INFO):
    logging.basicConfig(level=loglevel)
    loop = asyncio.get_event_loop()
    loop.create_task(proxy_mail(loop=loop))
    try:
        with aiomonitor.start_monitor(loop=loop):
            logging.info("Now you can connect with: nc localhost 50101")
            loop.run_forever()
    except KeyboardInterrupt:
        logging.info('Got KeyboardInterrupt')
