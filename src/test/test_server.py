import unittest
import logging
from email.message import EmailMessage
from email.headerregistry import Address
from email import message_from_bytes

from mail2alert import server


class GetLoglevelTests(unittest.TestCase):
    def test_default(self):
        self.assertEqual(logging.INFO, server.get_loglevel({}))

    def test_fatal(self):
        env = dict(LOGLEVEL='FATAL')
        self.assertEqual(logging.FATAL, server.get_loglevel(env))

    def test_wrong(self):
        env = dict(LOGLEVEL='debug')
        self.assertEqual(logging.INFO, server.get_loglevel(env))

    def test_misspelled(self):
        env = dict(LOGLEVEL='debugg')
        self.assertEqual(logging.INFO, server.get_loglevel(env))


class UpdateMailTests(unittest.TestCase):
    def test_update_mail_to_from(self):
        msg = EmailMessage()
        msg['Subject'] = 'a test'
        msg['From'] = Address('Test Sender', 'test_from', 'example.com')
        msg['To'] = [Address('Test %i' % i, 'test_%i' % i, 'example.com')
                     for i in range(2)]
        msg.set_content('test åäö')

        new_binary = server.update_mail_to_from(
            msg.as_bytes(),
            ['newto@example.com'],
            'newfrom@example.com'
        )

        new_msg = message_from_bytes(new_binary)
        self.assertEqual('newto@example.com', new_msg['To'])
        self.assertEqual('newfrom@example.com', new_msg['From'])

    def test_update_mail_to_from_roundtrip(self):
        msg = (
            b'Date: Wed, 19 Apr 2017 10:42:11 +0200\r\n'
            b'Sender: <go@pagero.com>\r\n'
            b'Reply-To: <go@pagero.com>\r\n'
            b'Subject: Stage [my-pipeline/6/my-stage/1] is broken\r\n'
            b'MIME-Version: 1.0\r\n'
            b'Content-Type: text/plain; charset="UTF-8"\r\n'
            b'Content-Transfer-Encoding: quoted-printable\r\n'
            b'Return-Path: go@pagero.com\r\n'
            b'To: mail2alert@example.com\r\n'
            b'From: go@pagero.com\r\n'
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

        new = server.update_mail_to_from(
            msg,
            ['mail2alert@example.com'],
            'go@pagero.com'
        )

        self.assertEqual(msg, new)

if __name__ == '__main__':
    unittest.main()
