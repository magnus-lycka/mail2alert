#!/usr/bin/env python3
import asyncio
import aiomonitor
from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Proxy
import logging

from .config import Configuration
from . import gocd

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


async def hearbeat(seconds_to_sleep=1):
    while 1:
        logging.debug('sleeping for: {0} seconds'.format(seconds_to_sleep))
        await asyncio.sleep(seconds_to_sleep)
        seconds_to_sleep *= 2


class Mail2AlertProxy(Proxy):
    def __init__(self, host, port, managers):
        self.mail2alert_managers = managers
        super().__init__(host, port)

    def _deliver(self, mailfrom, rcpttos, data):
        for manager in self.mail2alert_managers:
            if manager.wants_message(mailfrom, rcpttos, data):
                mailfrom, rcpttos, data = manager.process_message(mailfrom, rcpttos, data)
                break
        if rcpttos:
            return super()._deliver(mailfrom, rcpttos, data)


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
    managers = [globals()[manager['name']].Manager(manager) for manager in cnf['managers']]
    cont = Controller(
        Mail2AlertProxy(remote_host, remote_port, managers),
        hostname=local_host,
        port=local_port)
    cont.start()


def main():
    logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    loop.create_task(proxy_mail(loop=loop))
    loop.create_task(hearbeat())
    try:
        with aiomonitor.start_monitor(loop=loop):
            logging.info("Now you can connect with: nc localhost 50101")
            loop.run_forever()
    except KeyboardInterrupt:
        logging.info('Got KeyboardInterrupt')
