import unittest
import signal
import os
import re
import asyncio
import json
import logging
from aiohttp import web
from aiosmtpd.handlers import Debugging
from aiosmtpd.controller import Controller
from io import StringIO
from smtplib import SMTP
from email.message import EmailMessage
from email.headerregistry import Address
from multiprocessing import Process
from time import sleep

from mail2alert import server


# noinspection PyUnusedLocal
async def handle_get_pipeline_groups(request):
    pipeline_groups = [
        {
            "pipelines": [
                {"name": "my-pipeline"},
            ],
            "name": "my-group"
        },
    ]
    return web.Response(
        body=json.dumps(pipeline_groups).encode('utf-8'),
        content_type='application/json')


# noinspection PyUnusedLocal
async def handle_get_cctray(request):
    xml = '''<?xml version="1.0" encoding="utf-8"?>
    <Projects>
        <Project
            name="my-pipeline :: defaultStage"
            activity="Building"
            lastBuildStatus="Success"
            lastBuildLabel="1"
            lastBuildTime="2017-05-18T15:31:16"
            webUrl="http://localhost:8153/go/pipelines/p1/5/defaultStage/1"
        />
        <Project
            name="my-pipeline :: defaultStage :: defaultJob"
            activity="Building"
            lastBuildStatus="Success"
            lastBuildLabel="1"
            lastBuildTime="2017-05-18T15:31:16"
            webUrl="http://localhost:8153/go/tab/build/detail/p1/5/defaultStage/1/defaultJob"
        />
    </Projects>'''
    return web.Response(
        body=xml.encode('utf-8'),
        content_type='application/xml')


class ServerIntegrationTests(unittest.TestCase):
    app = None
    handler = None
    servers = None
    server_under_test = None

    @classmethod
    def setUpClass(cls):
        cls.config = {
            'remote_host': 'localhost',
            'remote_port': 1025,
            'local_host': 'localhost',
            'local_port': 8025,
        }
        cls.app = web.Application()
        cls.app.router.add_get(
            '/go/api/config/pipeline_groups',
            handle_get_pipeline_groups
        )
        cls.app.router.add_get(
            '/go/cctray.xml',
            handle_get_cctray
        )
        host = 'localhost'
        port = 8080
        loop = asyncio.get_event_loop()

        cls.handler = cls.app.make_handler(loop=loop)

        loop.run_until_complete(cls.app.startup())

        server_creation = loop.create_server(
            cls.handler, host, port, backlog=128
        )

        cls.servers = loop.run_until_complete(
            asyncio.gather(server_creation, loop=loop)
        )

        cls.server_under_test = Process(
            target=server.main,
            args=(logging.DEBUG,)
        )
        cls.server_under_test.start()
        sleep(0.03)

    @classmethod
    def tearDownClass(cls):
        server_under_test_pid = cls.server_under_test.pid
        os.kill(server_under_test_pid, signal.SIGINT)

        cls.server_under_test.terminate()

        loop = asyncio.get_event_loop()

        server_closures = []
        for srv in cls.servers:
            srv.close()
            server_closures.append(srv.wait_closed())
        loop.run_until_complete(asyncio.gather(*server_closures, loop=loop))
        loop.run_until_complete(cls.app.shutdown())
        loop.run_until_complete(cls.handler.shutdown(60.0))
        loop.run_until_complete(cls.app.cleanup())

    def setUp(self):
        self.data = StringIO()
        self.controller = Controller(
            Debugging(self.data),
            hostname=self.config['local_host'],
            port=self.config['local_port']
        )
        self.controller.start()

    def tearDown(self):
        self.controller.stop()

    def test_mail_proxy_pass(self):
        client = SMTP(self.config['remote_host'], self.config['remote_port'])
        msg = EmailMessage()
        msg['Subject'] = 'a test\r\n'
        msg['From'] = Address('Test Sender', 'test_from', 'example.com')
        msg['To'] = [Address('Test %i' % i, 'test_%i' % i, 'example.com')
                     for i in range(2)]
        msg.set_content('test åäö')
        client.send_message(msg)

        self.assertIn('Subject: a test', self.data.getvalue())
        self.assertIn('test åäö', self.data.getvalue())

    def test_mail_proxy_catch(self):
        client = SMTP(self.config['remote_host'], self.config['remote_port'])
        msg = EmailMessage()
        msg['Subject'] = 'Stage [my-pipeline/2/my-stage/1] is broken'
        msg['From'] = Address('Test Sender', 'test_from', 'example.com')
        msg['To'] = [Address('Mail2Alert', 'mail2alert', 'example.com')]
        msg.set_content('test åäö')
        client.send_message(msg)

        self.assertIn('Subject: Stage [my-pipeline/2/my-stage/1] is broken', self.data.getvalue())
        self.assertIn('cat@example.com', self.data.getvalue())
        self.assertIn('test åäö', self.data.getvalue())

    def test_mail_proxy_catch_big(self):
        client = SMTP(self.config['remote_host'], self.config['remote_port'])

        msg = (
            b'Date: Wed, 19 Apr 2017 10:42:11 +0200\r\n'
            b'From: <go@pagero.com>\r\n'
            b'Sender: <go@pagero.com>\r\n'
            b'Reply-To: <go@pagero.com>\r\n'
            b'To: <mail2alert@example.com>\r\n'
            b'Subject: Stage [my-pipeline/6/my-stage/1] is broken\r\n'
            b'MIME-Version: 1.0\r\n'
            b'Content-Type: text/plain; charset="UTF-8"\r\n'
            b'Content-Transfer-Encoding: quoted-printable\r\n'
            b'Return-Path: go@pagero.com\r\n'
            b'\r\n'
            b'See details: http://go.pagero.local/go/pipelines/create-pagero-online-relea=\r\n'
            b'se/6/SetupGoCDReleaseGroup/1\r\n'
            b'\r\n'
            b'-- CHECK-INS --\r\n'
            b'\r\n'
            b'Dependency: deploy-to-test/readyToTest\r\n'
            b'revision: deploy-to-test/881/readyToTest/1, completed on 2017-04-19 08:41:5=\r\n'
            b'5.272\r\n'
            b'\r\n'
            b'Git: ssh://git@git/config/gocd-create-group-of-pipelines\r\n'
            b'revision: 1f5557f803c998b7ae010dba9ff7fbdf71cab346, modified by Magnus Lyck=\r\n'
            b'=C3=A5 <magnusl@pagero.com> on 2017-03-15 16:31:40.0\r\n'
            b'remove temporary pipeline/repo-url fixes from create_group_of_pipelines.py\r\n'
            b'modified create_group_of_pipelines.py\r\n'
            b'\r\n'
            b'Dependency: deploy-to-staging/dummy\r\n'
            b'revision: deploy-to-staging/56/dummy/1, completed on 2017-03-13 17:42:18.88=\r\n'
            b'1\r\n'
            b'\r\n'
            b'Dependency: po-characterize-tests/runTests\r\n'
            b'revision: po-characterize-tests/3230/runTests/1, completed on 2016-12-19 15=\r\n'
            b':55:44.997\r\n'
            b'\r\n'
            b'Sent by Go on behalf of ex0247\r\n'
            b'\r\n'
        )

        expected = (
            '---------- MESSAGE FOLLOWS ----------\n'
            'mail options: [\'SIZE=1193\']\n\n'
            'Date: Wed, 19 Apr 2017 10:42:11 +0200\n'
            'Sender: <go@pagero.com>\n'
            'Reply-To: <go@pagero.com>\n'
            'Subject: Stage [my-pipeline/6/my-stage/1] is broken\n'
            'MIME-Version: 1.0\n'
            'Content-Type: text/plain; charset="UTF-8"\n'
            'Content-Transfer-Encoding: quoted-printable\n'
            'Return-Path: go@pagero.com\n'
            'X-Peer: 127.0.0.1\n'
            'To: cat@example.com\n'
            'From: go@pagero.com\n'
            'X-Peer: (\'127.0.0.1\', 39806)\n'
            '\n'
            'See details: http://go.pagero.local/go/pipelines/create-pagero-online-relea=\n'
            'se/6/SetupGoCDReleaseGroup/1\n'
            '\n'
            '-- CHECK-INS --\n'
            '\n'
            'Dependency: deploy-to-test/readyToTest\n'
            'revision: deploy-to-test/881/readyToTest/1, completed on 2017-04-19 08:41:5=\n'
            '5.272\n'
            '\n'
            'Git: ssh://git@git/config/gocd-create-group-of-pipelines\n'
            'revision: 1f5557f803c998b7ae010dba9ff7fbdf71cab346, modified by Magnus Lyck=\n'
            '=C3=A5 <magnusl@pagero.com> on 2017-03-15 16:31:40.0\n'
            'remove temporary pipeline/repo-url fixes from create_group_of_pipelines.py\n'
            'modified create_group_of_pipelines.py\n'
            '\n'
            'Dependency: deploy-to-staging/dummy\n'
            'revision: deploy-to-staging/56/dummy/1, completed on 2017-03-13 17:42:18.88=\n'
            '1\n'
            '\n'
            'Dependency: po-characterize-tests/runTests\n'
            'revision: po-characterize-tests/3230/runTests/1, completed on 2016-12-19 15=\n'
            ':55:44.997\n'
            '\n'
            'Sent by Go on behalf of ex0247\n'
            '------------ END MESSAGE ------------\n'
        )

        client.sendmail('go@pagero.com', ['mail2alert@example.com'], msg)

        self.maxDiff = None
        received = self.data.getvalue()
        received = re.sub(r"X-Peer: \('127.0.0.1', \d+\)", "X-Peer: ('127.0.0.1', 39806)", received)
        self.assertEqual(expected, received)

    def test_mail_proxy_drop(self):
        client = SMTP(self.config['remote_host'], self.config['remote_port'])
        msg = EmailMessage()
        msg['Subject'] = 'not my cup of tea'
        msg['From'] = Address('Test Sender', 'test_from', 'example.com')
        msg['To'] = [Address('Mail2Alert', 'mail2alert', 'example.com')]
        msg.set_content('test åäö')
        client.send_message(msg)

        self.assertEqual('', self.data.getvalue())

    def test_mail_proxy_backup(self):
        async def go():
            client = SMTP(self.config['remote_host'], self.config['remote_port'])
            for subject in (
                    "Server Backup Completed Successfully",
                    "Stage [my-pipeline/2/my-stage/1] failed",
                    "Server Backup Failed",
            ):
                msg = EmailMessage()
                msg['Subject'] = subject
                msg['From'] = Address('Go Eller', 'go', 'example.com')
                msg['To'] = [Address('admin', 'admin', 'example.com')]
                msg.set_content('test åäö')
                client.send_message(msg)

            await asyncio.sleep(0.05)

            self.assertIn('To: sys@example.com, op@example.com', self.data.getvalue())
            self.assertIn('Server Backup Completed Successfully', self.data.getvalue())
            self.assertIn('Server Backup Failed', self.data.getvalue())
            self.assertNotIn('my-pipeline', self.data.getvalue())

        loop = asyncio.get_event_loop()
        loop.run_until_complete(go())


if __name__ == '__main__':
    unittest.main()
