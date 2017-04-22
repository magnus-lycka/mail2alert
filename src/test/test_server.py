import unittest
from email.message import EmailMessage
from email.headerregistry import Address
from email import message_from_bytes

from mail2alert import server


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
