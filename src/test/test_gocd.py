import unittest
from unittest.mock import MagicMock

from mail2alert import gocd

pipeline_groups = [
    {
        "pipelines": [
            {"name": "a-build"},
            {"name": "a-test"},
        ],
        "name": "alpha"
    },
    {
        "pipelines": [
            {"name": "b-build"},
            {"name": "b-test"},
        ],
        "name": "beta"
    },
    {
        "pipelines": [
            {"name": "a-test-release-x",},
            {"name": "b-test-release-x",}
        ],
        "name": "release"
    },
]


class GocdPipelinesTests(unittest.TestCase):
    def test_filter_in_group(self):
        pipelines = gocd.Pipelines(pipeline_groups)

        filter = pipelines.in_group(group='beta')

        self.assertTrue(filter(dict(pipeline='b-build')))
        self.assertTrue(filter(dict(pipeline='b-test')))
        self.assertFalse(filter(dict(pipeline='b-test-release-x')))
        self.assertFalse(filter(dict(pipeline='a-test')))

    def test_filter_name_like_in_group(self):
        pipelines = gocd.Pipelines(pipeline_groups)

        filter = pipelines.name_like_in_group(re_pattern=r'(.+)-release.*', group='beta')

        self.assertFalse(filter(dict(pipeline='b-build')))
        self.assertFalse(filter(dict(pipeline='b-test')))
        self.assertTrue(filter(dict(pipeline='b-test-release-x')))
        self.assertFalse(filter(dict(pipeline='a-test')))


class GocdRuleTests(unittest.TestCase):
    def test_check_ok(self):
        msg = dict(event='BREAKS', pipeline='p1')
        conf = dict(
            filter=dict(
                events=['FAILS', 'BREAKS'],
                function='pipelines.in_group',
                args=['g1']
            ),
            actions=['mailto:a@b.c']
        )
        pipelines = gocd.Pipelines([{'name': 'g1',
                                     'pipelines': [{'name': 'p1'}]}])
        rule = gocd.GocdRule(conf)

        rcpts = rule.check(msg, dict(pipelines=pipelines))

        self.assertEqual(rcpts, conf['actions'])

    def test_check_wrong_event(self):
        msg = dict(event='CANCELLED', pipeline='p1')
        conf = dict(
            filter=dict(
                events=['FAILS', 'BREAKS'],
                function='pipelines.in_group',
                args=['g1']
            ),
            actions=['mailto:a@b.c']
        )
        pipelines = gocd.Pipelines([{'name': 'g1',
                                     'pipelines': [{'name': 'p1'}]}])
        rule = gocd.GocdRule(conf)

        rcpts = rule.check(msg, dict(pipelines=pipelines))

        self.assertEqual(rcpts, [])

    def test_check_wrong_pipeline(self):
        msg = MagicMock(event='BREAKS', pipeline='p2')
        conf = dict(
            filter=dict(
                events=['FAILS', 'BREAKS'],
                function='pipelines.in_group',
                args=['g1']
            ),
            actions=['mailto:a@b.c']
        )
        pipelines = gocd.Pipelines([{'name': 'g1',
                                     'pipelines': [{'name': 'p1'}]}])
        rule = gocd.GocdRule(conf)

        rcpts = rule.check(msg, dict(pipelines=pipelines))

        self.assertEqual(rcpts, [])


class ManagerTests(unittest.TestCase):
    def test_wants_message_from(self):
        conf = {'message-we-want': {'from': 'krumelur@example.com'}}
        mgr = gocd.Manager(conf)

        wants = mgr.wants_message('krumelur@example.com', [], '')

        self.assertTrue(wants)

    def test_wants_not_message_from(self):
        conf = {'message-we-want': {'from': 'krumelur@example.com'}}
        mgr = gocd.Manager(conf)

        wants = mgr.wants_message('easterbunny@example.com', [], '')

        self.assertFalse(wants)

    def test_wants_message_to(self):
        conf = {'message-we-want': {'to': 'krumelur@example.com'}}
        mgr = gocd.Manager(conf)

        wants = mgr.wants_message('', ['krumelur@example.com'], '')

        self.assertTrue(wants)


    def test_wants_not_message_to(self):
        conf = {'message-we-want': {'to': 'not@example.com'}}
        mgr = gocd.Manager(conf)

        wants = mgr.wants_message('', ['krumelur@example.com'], '')

        self.assertFalse(wants)

    def test_test(self):
        pipeline_groups = [
            {
                'name': 'g1',
                'pipelines': [
                    {'name': 'p11', 'extra': 'removed'},
                    {'name': 'p12'},
                ]
            },
            {
                'name': 'g2',
                'pipelines': [
                    {'name': 'p21'},
                ]
            },
        ]
        rules = [
            {
                'actions': ['mailto:we@example.com'],
                'filter': {
                    'events': ['BREAKS', 'FIXED'],
                    'function': 'pipelines.in_group',
                    'args': ['g1']
                }
            },
            {
                'actions': ['mailto:them@example.com'],
                'filter': {
                    'events': ['FAILS'],
                    'function': 'pipelines.in_group',
                    'args': ['g2']
                }
            },
        ]
        expectecd = [
            {
                'name': 'g1',
                'pipelines': [
                    {
                        'name': 'p11',
                        'rules': [
                            {
                                'actions': ['mailto:we@example.com'],
                                'events': ['BREAKS', 'FIXED']
                            }
                        ]
                    },
                    {
                        'name': 'p12',
                        'rules': [
                            {
                                'actions': ['mailto:we@example.com'],
                                'events': ['BREAKS', 'FIXED']
                            }
                        ]
                    },
                ]
            },
            {
                'name': 'g2',
                'pipelines': [
                    {
                        'name': 'p21',
                        'rules': [
                            {
                                'actions': ['mailto:them@example.com'],
                                'events': ['FAILS']
                            }
                        ]
                    },
                ]
            },
        ]
        mgr = gocd.Manager(dict(rules=rules))
        mgr.pipeline_groups = pipeline_groups

        actual = mgr.test()

        self.assertEqual(actual, expectecd)

if __name__ == '__main__':
    unittest.main()
