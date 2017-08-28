import unittest
from unittest.mock import MagicMock

from mail2alert import actions


class ActionsTests(unittest.TestCase):
    def test_mail_actions(self):

        act = actions.Actions(['mailto:a@b.c', 'mailto:d@e.f'])

        self.assertEqual([a.destination for a in act.mailto], ['a@b.c', 'd@e.f'])

    def test_mixed_actions(self):
        actions.logging = MagicMock()

        act = actions.Actions([
            'mailto:a@b.c',
            'mailtoooooo:d@e.f',
            'slack:#channel',
            'slack:@user:full'
        ])

        self.assertEqual([a.destination for a in act.mailto], ['a@b.c'])
        self.assertEqual([a.destination for a in act.slack], ['#channel', '@user'])
        self.assertEqual([a.style for a in act.slack], ['brief', 'full'])
        # noinspection PyUnresolvedReferences
        actions.logging.error.assert_called_with('Unexpected action: mailtoooooo:d@e.f')


if __name__ == '__main__':
    unittest.main()
