import unittest

import mail2alert.rules

class RuleTests(unittest.TestCase):
    def test_make_rule(self):
        owner = 'o'
        name = 'n'
        filter = {
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
            filter=filter,
            actions=actions
        )

        rule = mail2alert.rules.Rule(rule_dict)

        self.assertEqual(rule.owner, owner)
        self.assertEqual(rule.name, name)
        self.assertEqual(rule.filter, filter)
        self.assertEqual(rule.actions, actions)

    def test_make_null_rule(self):

        rule = mail2alert.rules.Rule({})

        self.assertEqual(rule.owner, '')
        self.assertEqual(rule.name, '')
        self.assertEqual(rule.filter, {})
        self.assertEqual(rule.actions, [])
