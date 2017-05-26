import unittest
from unittest.mock import MagicMock

from mail2alert import actions


class ActionsTests(unittest.TestCase):
    def test_mail_actions(self):

        act = actions.Actions(['mailto:a@b.c', 'mailto:d@e.f'])

        self.assertEqual(act.mailto, ['a@b.c', 'd@e.f'])

    def test_mixed_actions(self):
        actions.logging = MagicMock()

        act = actions.Actions(['mailto:a@b.c', 'mailtoooooo:d@e.f'])

        self.assertEqual(act.mailto, ['a@b.c'])
        # noinspection PyUnresolvedReferences
        actions.logging.error.assert_called_with('Unexpected action: mailtoooooo:d@e.f')


if __name__ == '__main__':
    unittest.main()
