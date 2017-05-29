import asyncio
import unittest
from collections import defaultdict
from email.message import EmailMessage

from mail2alert.plugin import gocd


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

    def test_filter_in_group_which_does_not_exist(self):
        pipelines = gocd.Pipelines(self.pipeline_groups)

        rule_filter = pipelines.in_group(group='betaxxx')

        self.assertFalse(rule_filter(dict(pipeline='b-build')))
        self.assertFalse(rule_filter(dict(pipeline='b-test')))
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

        rule_filter = pipelines.any()

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
        mgr._pipeline_groups = [
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

        loop = asyncio.get_event_loop()
        test_task = loop.create_task(mgr.test_msgs())
        loop.run_until_complete(test_task)
        actual = test_task.result()

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
                    'function': 'pipelines.any',
                }
            },
        ]
        expected = [
            {
                'pipeline_group': 'g1',
                'pipelines': [
                    {
                        'pipeline': 'p11',
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
                        'pipeline': 'p12',
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
                'pipeline_group': 'g2',
                'pipelines': [
                    {
                        'pipeline': 'p21',
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
        mgr._pipeline_groups = pipeline_groups

        loop = asyncio.get_event_loop()
        test_task = loop.create_task(mgr.test())
        loop.run_until_complete(test_task)
        actual = test_task.result()

        self.maxDiff = 10000
        self.assertEqual(actual, expected)

    def test_process_message_edge_detect(self):
        """
        test_process_message
        If previous state was successful (fixed or passed) and the current
        state is a failure, it's a BREAKS, even if the message says "failed"
        instead of "is broken".
        Same thing other way: "passed" => "is fixed" if previous was a fail.
        """

        async def check_process_message(process_message_future):
            rules = [
                {
                    'actions': ['mailto:nosy@example.com'],
                    'filter': {
                        'events': ['BREAKS'],
                        'function': 'pipelines.any',
                    }
                },
            ]
            mgr = gocd.Manager(dict(rules=rules))
            mgr.previous_pipeline_state = defaultdict(gocd.BuildStateSuccess)

            mail_from = 'sender@example.com'
            rcpt_tos = ['receiver@example.com']
            msg = EmailMessage()
            msg['Subject'] = 'Stage [my-pipeline/232/my-stage/1] failed'
            msg['From'] = mail_from
            msg['To'] = rcpt_tos
            msg.set_content('test')

            process_message_future.set_result(
                await mgr.process_message(mail_from, rcpt_tos, msg.as_bytes())
            )

        loop = asyncio.get_event_loop()
        future = asyncio.Future()
        asyncio.ensure_future(check_process_message(future))
        loop.run_until_complete(future)
        sender, receiver, body = future.result()

        self.assertEqual('sender@example.com', sender)
        self.assertEqual(['nosy@example.com'], receiver)
        self.assertIn(b'failed', body)


class MessageTests(unittest.TestCase):
    def test_parse_fixed_pipeline(self):
        mail = EmailMessage()
        mail['Subject'] = 'Stage [my-pipeline/232/my-stage/1] is fixed'

        msg = gocd.Message(mail.as_bytes())

        self.assertEqual(gocd.Event.FIXED, msg['event'])
        self.assertEqual('my-pipeline', msg['pipeline'])

    def test_parse_breaks_pipeline(self):
        mail = EmailMessage()
        mail['Subject'] = 'Stage [my-pipeline/232/my-stage/1] is broken'

        msg = gocd.Message(mail.as_bytes())

        self.assertEqual(gocd.Event.BREAKS, msg['event'])
        self.assertEqual('my-pipeline', msg['pipeline'])

    def test_parse_cancelled_pipeline(self):
        mail = EmailMessage()
        mail['Subject'] = 'Stage [my-pipeline/232/my-stage/1] is cancelled'

        msg = gocd.Message(mail.as_bytes())

        self.assertEqual(gocd.Event.CANCELLED, msg['event'])
        self.assertEqual('my-pipeline', msg['pipeline'])

    def test_parse_passes_pipeline(self):
        mail = EmailMessage()
        mail['Subject'] = 'Stage [my-pipeline/232/my-stage/1] passed'

        msg = gocd.Message(mail.as_bytes())

        self.assertEqual(gocd.Event.PASSES, msg['event'])
        self.assertEqual('my-pipeline', msg['pipeline'])

    def test_parse_fails_pipeline(self):
        mail = EmailMessage()
        mail['Subject'] = 'Stage [my-pipeline/232/my-stage/1] failed'

        msg = gocd.Message(mail.as_bytes())

        self.assertEqual(gocd.Event.FAILS, msg['event'])
        self.assertEqual('my-pipeline', msg['pipeline'])

    def test_parse_linefeed_in_subject(self):
        bmail = b'Subject: Stage [my-pipeline/2/stage/1] \r\n failed\r\n\r\n'

        msg = gocd.Message(bmail)

        self.assertEqual(gocd.Event.FAILS, msg['event'])
        self.assertEqual('my-pipeline', msg['pipeline'])

    def test_parse_event_mismatching_history_failed_breaks(self):
        bmail = b'Subject: Stage [my_pipeline/2/stage/1] \r\n failed\r\n\r\n'

        previous_states = dict(my_pipeline=gocd.BuildStateSuccess())
        msg = gocd.Message(bmail, previous_states=previous_states)

        self.assertEqual(gocd.Event.BREAKS, msg['event'])
        self.assertEqual('my_pipeline', msg['pipeline'])
        self.assertEqual(previous_states['my_pipeline'], gocd.BuildStateFailure())

    def test_parse_event_mismatching_history_breaks_failed(self):
        bmail = b'Subject: Stage [my_pipeline/2/stage/1] \r\n is broken\r\n\r\n'

        previous_states = dict(my_pipeline=gocd.BuildStateFailure())
        msg = gocd.Message(bmail, previous_states=previous_states)

        self.assertEqual(gocd.Event.BREAKS, msg['event'])
        self.assertEqual('my_pipeline', msg['pipeline'])
        self.assertEqual(previous_states['my_pipeline'], gocd.BuildStateFailure())


    def test_parse_event_mismatching_history_passed_fixed(self):
        bmail = b'Subject: Stage [my_pipeline/2/stage/1] \r\n passed\r\n\r\n'

        previous_states = dict(my_pipeline=gocd.BuildStateFailure())
        msg = gocd.Message(bmail, previous_states=previous_states)

        self.assertEqual(gocd.Event.FIXED, msg['event'])
        self.assertEqual('my_pipeline', msg['pipeline'])
        self.assertEqual(previous_states['my_pipeline'], gocd.BuildStateSuccess())

    def test_parse_event_mismatching_history_fixed_passed(self):
        bmail = b'Subject: Stage [my_pipeline/2/stage/1] \r\n is fixed\r\n\r\n'

        previous_states = dict(my_pipeline=gocd.BuildStateSuccess())
        msg = gocd.Message(bmail, previous_states=previous_states)

        self.assertEqual(gocd.Event.FIXED, msg['event'])
        self.assertEqual('my_pipeline', msg['pipeline'])
        self.assertEqual(previous_states['my_pipeline'], gocd.BuildStateSuccess())

    def test_parse_unexpected(self):
        mail = EmailMessage()
        mail['Subject'] = 'Stage [my-pipeline/232/my-stage/1] other'

        msg = gocd.Message(mail.as_bytes())

        self.assertEqual(None, msg['event'])
        self.assertEqual('my-pipeline', msg['pipeline'])


class BuildStateTests(unittest.TestCase):
    def test_green_to_green(self):

        self.assertEqual(gocd.BuildStateSuccess().after(gocd.BuildStateSuccess()), gocd.Event.PASSES)

    def test_red_to_green(self):

        self.assertEqual(gocd.BuildStateSuccess().after(gocd.BuildStateFailure()), gocd.Event.FIXED)

    def test_unknown_to_green(self):

        self.assertEqual(gocd.BuildStateSuccess().after(gocd.BuildStateUnknown()), gocd.Event.FIXED)

    def test_green_to_red(self):

        self.assertEqual(gocd.BuildStateFailure().after(gocd.BuildStateSuccess()), gocd.Event.BREAKS)

    def test_red_to_red(self):

        self.assertEqual(gocd.BuildStateFailure().after(gocd.BuildStateFailure()), gocd.Event.FAILS)

    def test_unknown_to_red(self):
        self.assertEqual(gocd.BuildStateFailure().after(gocd.BuildStateUnknown()), gocd.Event.BREAKS)

    def test_something_to_unknown(self):
        self.assertEqual(gocd.BuildStateUnknown().after(gocd.BuildStateUnknown()), None)

    def test_get_state_from_event_pass(self):

        self.assertEqual(gocd.build_state_factory(event=gocd.Event.PASSES), gocd.BuildStateSuccess())

    def test_get_state_from_event_fixed(self):

        self.assertEqual(gocd.build_state_factory(event=gocd.Event.FIXED), gocd.BuildStateSuccess())

    def test_get_state_from_event_fails(self):

        self.assertEqual(gocd.build_state_factory(event=gocd.Event.FAILS), gocd.BuildStateFailure())

    def test_get_state_from_event_breaks(self):

        self.assertEqual(gocd.build_state_factory(event=gocd.Event.BREAKS), gocd.BuildStateFailure())

    def test_get_state_from_event_cancelled(self):

        self.assertEqual(gocd.build_state_factory(event=gocd.Event.CANCELLED), gocd.BuildStateUnknown())

    def test_get_state_from_lastBuildStatus_success(self):

        self.assertEqual(gocd.build_state_factory(last_build_status='Success'), gocd.BuildStateSuccess())

    def test_get_state_from_lastBuildStatus_failure(self):

        self.assertEqual(gocd.build_state_factory(last_build_status='Failure'), gocd.BuildStateFailure())


if __name__ == '__main__':
    unittest.main()
