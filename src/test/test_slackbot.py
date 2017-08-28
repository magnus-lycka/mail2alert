import asyncio
import unittest
from asynctest import CoroutineMock

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
        self.assertEqual(attachment, sm.full_attachment)

    def test_post_messages(self):
        SlackMessage.post_full = CoroutineMock()
        SlackMessage.post_brief = CoroutineMock()

        class MockAction:
            def __init__(self, destination, style):
                self.destination = destination
                self.style = style

        slactions = [MockAction('#chanel', 'full'), MockAction('@tjo', 'brief')]

        m = Message(b'message')
        m['Subject'] = 'sub'
        m['From'] = 'me'
        sm = SlackMessage(m)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(sm.post(slactions))

        SlackMessage.post_full.assert_called_once()
        SlackMessage.post_brief.assert_called_once()


if __name__ == '__main__':
    unittest.main()
