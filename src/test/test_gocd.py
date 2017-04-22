import unittest

from mail2alert import gocd


class GocdPipelinesTests(unittest.TestCase):
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
                {"name": "a-test-release-x"},
                {"name": "b-test-release-x"}
            ],
            "name": "release"
        },
    ]

    def test_filter_in_group(self):
        pipelines = gocd.Pipelines(self.pipeline_groups)

        rule_filter = pipelines.in_group(group='beta')

        self.assertTrue(rule_filter(dict(pipeline='b-build')))
        self.assertTrue(rule_filter(dict(pipeline='b-test')))
        self.assertFalse(rule_filter(dict(pipeline='b-test-release-x')))
        self.assertFalse(rule_filter(dict(pipeline='a-test')))

    def test_filter_name_like_in_group(self):
        pipelines = gocd.Pipelines(self.pipeline_groups)

        rule_filter = pipelines.name_like_in_group(
            re_pattern=r'(.+)-release.*',
            group='beta'
        )

        self.assertFalse(rule_filter(dict(pipeline='b-build')))
        self.assertFalse(rule_filter(dict(pipeline='b-test')))
        self.assertTrue(rule_filter(dict(pipeline='b-test-release-x')))
        self.assertFalse(rule_filter(dict(pipeline='a-test')))

    def test_filter_all(self):
        pipelines = gocd.Pipelines(self.pipeline_groups)

        rule_filter = pipelines.all()

        self.assertTrue(rule_filter(dict(pipeline='b-build')))
        self.assertTrue(rule_filter(dict(pipeline='b-test')))
        self.assertTrue(rule_filter(dict(pipeline='b-test-release-x')))
        self.assertTrue(rule_filter(dict(pipeline='a-test')))


class GocdRuleTests(unittest.TestCase):
    def test_check_ok(self):
        msg = dict(event=gocd.Event.BREAKS, pipeline='p1')
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
        msg = dict(event=gocd.Event.CANCELLED, pipeline='p1')
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
        msg = dict(event=gocd.Event.BREAKS, pipeline='p2')
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

    def test_check_no_event(self):
        msg = dict(event=None, pipeline='p2')
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

    def test_check_no_event_in_rule(self):
        msg = dict(event=gocd.Event.BREAKS, pipeline='p1')
        conf = dict(
            filter=dict(
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


class ManagerTests(unittest.TestCase):
    def test_wants_message_from(self):
        conf = {'messages-we-want': {'from': 'krumelur@example.com'}}
        mgr = gocd.Manager(conf)

        wants = mgr.wants_message('krumelur@example.com', [], '')

        self.assertTrue(wants)

    def test_wants_not_message_from(self):
        conf = {'messages-we-want': {'from': 'krumelur@example.com'}}
        mgr = gocd.Manager(conf)

        wants = mgr.wants_message('easterbunny@example.com', [], '')

        self.assertFalse(wants)

    def test_wants_message_to(self):
        conf = {'messages-we-want': {'to': 'krumelur@example.com'}}
        mgr = gocd.Manager(conf)

        wants = mgr.wants_message('', ['krumelur@example.com'], '')

        self.assertTrue(wants)

    def test_wants_not_message_to(self):
        conf = {'messages-we-want': {'to': 'not@example.com'}}
        mgr = gocd.Manager(conf)

        wants = mgr.wants_message('', ['krumelur@example.com'], '')

        self.assertFalse(wants)

    def test_test_msgs(self):
        mgr = gocd.Manager(dict())
        mgr.pipeline_groups = [
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
        expected = [
            dict(event=gocd.Event.BREAKS, pipeline='p11'),
            dict(event=gocd.Event.CANCELLED, pipeline='p11'),
            dict(event=gocd.Event.FAILS, pipeline='p11'),
            dict(event=gocd.Event.FIXED, pipeline='p11'),
            dict(event=gocd.Event.PASSES, pipeline='p11'),
            dict(event=gocd.Event.BREAKS, pipeline='p12'),
            dict(event=gocd.Event.CANCELLED, pipeline='p12'),
            dict(event=gocd.Event.FAILS, pipeline='p12'),
            dict(event=gocd.Event.FIXED, pipeline='p12'),
            dict(event=gocd.Event.PASSES, pipeline='p12'),
            dict(event=gocd.Event.BREAKS, pipeline='p21'),
            dict(event=gocd.Event.CANCELLED, pipeline='p21'),
            dict(event=gocd.Event.FAILS, pipeline='p21'),
            dict(event=gocd.Event.FIXED, pipeline='p21'),
            dict(event=gocd.Event.PASSES, pipeline='p21'),
        ]

        actual = mgr.test_msgs()

        self.maxDiff = 1000
        self.assertEqual(list(actual), expected)

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
            {
                'actions': ['mailto:nosy@example.com'],
                'filter': {
                    'events': ['FAILS', 'CANCELLED'],
                    'function': 'pipelines.all',
                }
            },
        ]
        expected = [
            {
                'name': 'g1',
                'pipelines': [
                    {
                        'name': 'p11',
                        'alerts': [
                            {
                                'actions': ['mailto:we@example.com'],
                                'events': ['BREAKS', 'FIXED']
                            },
                            {
                                'actions': ['mailto:nosy@example.com'],
                                'events': ['CANCELLED', 'FAILS']
                            },
                        ]
                    },
                    {
                        'name': 'p12',
                        'alerts': [
                            {
                                'actions': ['mailto:we@example.com'],
                                'events': ['BREAKS', 'FIXED']
                            },
                            {
                                'actions': ['mailto:nosy@example.com'],
                                'events': ['CANCELLED', 'FAILS']
                            },
                        ]
                    },
                ]
            },
            {
                'name': 'g2',
                'pipelines': [
                    {
                        'name': 'p21',
                        'alerts': [
                            {
                                'actions': ['mailto:nosy@example.com'],
                                'events': ['CANCELLED', 'FAILS']
                            },
                            {
                                'actions': ['mailto:them@example.com'],
                                'events': ['FAILS']
                            },
                        ]
                    },
                ]
            },
        ]
        mgr = gocd.Manager(dict(rules=rules))
        mgr.pipeline_groups = pipeline_groups

        actual = mgr.test()

        self.maxDiff = 10000
        self.assertEqual(actual, expected)


class MessageTests(unittest.TestCase):
    def test_parse_fixed_pipeline(self):
        mailtext = (
            "blah blah blah\n"
            "Subject: Stage [my-pipeline/232/my-stage/1] is fixed\n"
            "blah blah blah"
        )

        msg = gocd.Message(mailtext.encode())

        self.assertEqual(gocd.Event.FIXED, msg['event'])
        self.assertEqual('my-pipeline', msg['pipeline'])

    def test_parse_breaks_pipeline(self):
        mailtext = (
            "blah blah blah\n"
            "Subject: Stage [my-pipeline/232/my-stage/1] is broken\n"
            "blah blah blah"
        )

        msg = gocd.Message(mailtext.encode())

        self.assertEqual(gocd.Event.BREAKS, msg['event'])
        self.assertEqual('my-pipeline', msg['pipeline'])

    def test_parse_cancelled_pipeline(self):
        mailtext = (
            "blah blah blah\n"
            "Subject: Stage [my-pipeline/232/my-stage/1] is cancelled\n"
            "blah blah blah"
        )

        msg = gocd.Message(mailtext.encode())

        self.assertEqual(gocd.Event.CANCELLED, msg['event'])
        self.assertEqual('my-pipeline', msg['pipeline'])

    def test_parse_passes_pipeline(self):
        mailtext = (
            "blah blah blah\n"
            "Subject: Stage [my-pipeline/232/my-stage/1] passed\n"
            "blah blah blah"
        )

        msg = gocd.Message(mailtext.encode())

        self.assertEqual(gocd.Event.PASSES, msg['event'])
        self.assertEqual('my-pipeline', msg['pipeline'])

    def test_parse_fails_pipeline(self):
        mailtext = (
            "blah blah blah\n"
            "Subject: Stage [my-pipeline/232/my-stage/1] failed \n"
            "blah blah blah"
        )

        msg = gocd.Message(mailtext.encode())

        self.assertEqual(gocd.Event.FAILS, msg['event'])
        self.assertEqual('my-pipeline', msg['pipeline'])

    def test_parse_unexpected(self):
        mailtext = (
            "blah blah blah\n"
            "Subject: Stage [my-pipeline/232/my-stage/1] other\n"
            "blah blah blah"
        )

        msg = gocd.Message(mailtext.encode())

        self.assertEqual(None, msg['event'])
        self.assertEqual('my-pipeline', msg['pipeline'])

if __name__ == '__main__':
    unittest.main()
