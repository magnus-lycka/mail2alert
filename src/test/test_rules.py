import unittest

import mail2alert.rules


class RuleTests(unittest.TestCase):
    def test_make_rule(self):
        owner = 'o'
        name = 'n'
        rule_filter = {
            'events': [
                'FAILS',
                'BREAKS',
                'FIXED',
            ],
            'function': 'pipelines.in_group',
            'args': ['my_group']
        }
        actions = '[mailto:a@b.c]'

        rule_dict = dict(
            owner=owner,
            name=name,
            filter=rule_filter,
            actions=actions
        )

        rule = mail2alert.rules.Rule(rule_dict)

        self.assertEqual(rule.owner, owner)
        self.assertEqual(rule.name, name)
        self.assertEqual(rule.filter, rule_filter)
        self.assertEqual(rule.actions, actions)

    def test_make_null_rule(self):
        rule = mail2alert.rules.Rule({})

        self.assertEqual(rule.owner, '')
        self.assertEqual(rule.name, '')
        self.assertEqual(rule.filter, {})
        self.assertEqual(rule.actions, [])

    def test_basic_check_ok(self):
        msg = {'subject': 'nuff'}
        functions = {
            'rule_tests': self
        }
        actions = ['mailto:a@b.c']
        rule = mail2alert.rules.Rule(
            dict(
                filter=dict(function='rule_tests.helper_for_test_basic_check'),
                actions=actions
            )
        )

        self.assertEqual(['mailto:a@b.c'], rule.check(msg, functions))

    def test_basic_check_fail(self):
        msg = {'subject': 'niff'}
        functions = {
            'rule_tests': self
        }
        actions = ['mailto:a@b.c']
        rule = mail2alert.rules.Rule(
            dict(
                filter=dict(function='rule_tests.helper_for_test_basic_check'),
                actions=actions
            )
        )

        self.assertEqual([], rule.check(msg, functions))

    @staticmethod
    def helper_for_test_basic_check(*args):
        def f(msg):
            return msg['subject'] == 'nuff'

        return f

if __name__ == '__main__':
    unittest.main()
