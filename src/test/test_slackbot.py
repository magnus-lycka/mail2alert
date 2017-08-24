import unittest
from mail2alert.slackbot import SlackMessage
from mail2alert.plugin.mail import Message


class SlackMessageTests(unittest.TestCase):
    def test_make_message(self):
        m = Message(b'Blah blah...\n')
        m['From'] = 'a@b'
        m['Subject'] = 'Subject Line'
        sm = SlackMessage(m)

        attachment = {
            'title': 'Subject Line',
            'text': 'Blah blah...\n',
            'color': '#4ABCF9'
        }

        self.assertEqual('Message from: a@b', sm.text)
        self.assertEqual(attachment, sm.attachment)


if __name__ == '__main__':
    unittest.main()
