import unittest
from email.message import EmailMessage

from mail2alert.plugin import mail


class MailMessage(unittest.TestCase):
    def test_message(self):
        email = EmailMessage()
        email['Subject'] = 'About'
        email['From'] = 'sen@der'
        email['To'] = 'receiver'
        email.set_content('body body body.')

        msg = mail.Message(email.as_bytes())
        msg['To'] = 'Override To'
        msg['extra'] = 'extra'

        self.assertEqual(msg['Subject'], email['Subject'])
        self.assertEqual(msg.get('From'), email['From'])
        self.assertEqual(msg['To'], 'Override To')
        self.assertEqual(msg['extra'], 'extra')
        self.assertEqual(msg.body, 'body body body.\n')


if __name__ == '__main__':
    unittest.main()
