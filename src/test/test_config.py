import unittest

import mail2alert.config


class ConfigTests(unittest.TestCase):
    def test_read_config(self):
        conf = mail2alert.config.Configuration()

        self.assertEqual(conf['local-smtp'], 'localhost:1025')

if __name__ == '__main__':
    unittest.main()
