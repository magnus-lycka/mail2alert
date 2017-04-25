import unittest
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


class ServerIntegrationTests(unittest.TestCase):
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
        host = 'localhost'
        port = 8080
        loop = asyncio.get_event_loop()

        cls.handler = cls.app.make_handler(loop=loop)

        loop.run_until_complete(cls.app.startup())

        server_creation=loop.create_server(
            cls.handler, host, port, backlog=128
        )

        cls.servers = loop.run_until_complete(
            asyncio.gather(server_creation, loop=loop)
        )

        cls.server_under_test = Process(
            target=server.main,
            args=(logging.WARNING,)
        )
        cls.server_under_test.start()
        sleep(0.03)

    def setUp(self):
        self.data = StringIO()
        self.controller = Controller(Debugging(self.data),
                                    hostname=self.config['local_host'],
                                    port=self.config['local_port'])
        self.controller.start()

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

    def test_mail_proxy_drop(self):
        client = SMTP(self.config['remote_host'], self.config['remote_port'])
        msg = EmailMessage()
        msg['Subject'] = 'not my cup of tea'
        msg['From'] = Address('Test Sender', 'test_from', 'example.com')
        msg['To'] = [Address('Mail2Alert', 'mail2alert', 'example.com')]
        msg.set_content('test åäö')
        client.send_message(msg)

        self.assertEquals('', self.data.getvalue())

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

    def tearDown(self):
        self.controller.stop()

    @classmethod
    def tearDownClass(cls):
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


if __name__ == '__main__':
    unittest.main()


