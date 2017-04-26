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


if __name__ == '__main__':
    unittest.main()
