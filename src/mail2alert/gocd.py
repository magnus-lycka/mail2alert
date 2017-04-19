from enum import Enum, auto
from itertools import product
import logging
import re

from mail2alert.rules import Rule
from .actions import Actions


class Manager:
    """
    gocd.Manager objects are handed mail messages.

    Based on the mail2alert configuration and knowledge about the
    GoCD server configuration, they determine what to do with the
    mail message.
    """

    def __init__(self, conf):
        self.conf = conf
        self.pipeline_groups = []

    def wants_message(self, mail_from, rcpt_tos, content):
        """
        Determine whether the manager is interested in a certain message.
        """
        wanted = self.conf['message-we-want']
        wanted_to = wanted.get('to')
        if wanted_to:
            return wanted_to in rcpt_tos
        wanted_from = wanted.get('from')
        if wanted_from:
            return wanted_from == mail_from

    def process(self, mail_from, rcpt_tos, content):
        recipients = []
        msg = Message(content)
        for rule in get_rules(self.conf['rules']):
            actions = Actions(rule.check(msg, {'pipelines': Pipelines(self.pipeline_groups)}))
            recipients.extend(actions.mailto)
        return mail_from, recipients, content

    def test(self):
        """
        This method can be used both to check that the configuration is correct,
        and to produce a report about where alerts go.
        """
        report = []
        pipeline_map = {}
        for pipeline_group in self.pipeline_groups:
            group_report = {
                'name': pipeline_group['name'],
                'pipelines': [{'name': p['name']} for p in pipeline_group['pipelines']]
            }
            report.append(group_report)
            for pipeline_report in group_report['pipelines']:
                pipeline_map[pipeline_report['name']] = pipeline_report

        for msg in self.test_msgs():
            for rule in get_rules(self.conf['rules']):
                if rule.check(msg, {'pipelines': Pipelines(self.pipeline_groups)}):
                    logging.debug('msg', msg, 'checks for rule', rule)
                    self.add_alert_to_report(msg, rule, pipeline_map)
        return report

    def test_msgs(self):
        pipelines = []
        for grp in self.pipeline_groups:
            pipelines.extend([p['name'] for p in grp['pipelines']])
        return (dict(pipeline=p, event=e) for p, e in product(pipelines, Event.names()))

    @staticmethod
    def add_alert_to_report(msg, rule, pipeline_map):
        pipeline_dict = pipeline_map[msg['pipeline']]
        alerts = pipeline_dict.setdefault('alerts', [])
        for candidate in alerts:
            if rule.actions == candidate['actions']:
                alert = candidate
                break
        else:
            alert = dict(actions=rule.actions, events=[])
            alerts.append(alert)
        if msg['event'] not in alert['events']:
            alert['events'].append(msg['event'])


class GocdRule(Rule):
    def check(self, msg, functions):
        """
        Extract which pipeline and which event from the msg, and test with the filter
        """
        if not msg['event'] in self.filter['events']:
            return []
        key, method = self.filter['function'].split('.')
        rule_filter = getattr(functions[key], method)(*tuple(self.filter.get('args', ())))
        if rule_filter(msg):
            return self.actions
        return []


def get_rules(rule_list):
    for rule in rule_list:
        yield GocdRule(rule)


class Event(Enum):
    BREAKS = auto()
    CANCELLED = auto()
    FAILS = auto()
    FIXED = auto()
    PASSES = auto()

    @classmethod
    def names(cls):
        return list(cls.__members__.keys())


class Message(dict):
    def __init__(self, content):
        event_map = {
            'is fixed': Event.FIXED.name,
            'is broken': Event.BREAKS.name,
            'is cancelled': Event.CANCELLED.name,
            'passed': Event.PASSES.name,
            'failed': Event.FAILS.name,
        }
        super().__init__()
        pattern = re.compile(r'Subject: Stage \[([^/]+)/[^/]+/[^/]+/[^/]+\] (.+)$', re.M)
        mo = pattern.search(content)
        if mo:
            event = event_map.get(mo.group(2).strip())
            if not event:
                logging.warning('Unexpected event "%s" in %r' % (mo.group(2), content))
            self['pipeline'] = mo.group(1)
            self['event'] = event
        else:
            logging.warning('Unable to parse message: %r' % content)
            self['pipeline'] = None
            self['event'] = None


class Pipelines:
    """
    This class should be passed the content from go/api/config/pipeline_groups
    """

    def __init__(self, config_listing):
        self._config_listing = config_listing

    def _get_group_pipelines(self, group):
        for pipeline_group in self._config_listing:
            if pipeline_group['name'] == group:
                return pipeline_group['pipelines']

    @staticmethod
    def all():
        return lambda msg: True

    def in_group(self, group):
        def in_group_filter(msg):
            for pipeline_instance in self._get_group_pipelines(group):
                if pipeline_instance['name'] == msg['pipeline']:
                    return True
            return False

        return in_group_filter

    def name_like_in_group(self, re_pattern, group):
        def name_like_in_group_filter(msg):
            mo = re.search(re_pattern, msg['pipeline'])
            if not mo:
                return False
            matched_pipeline = mo.group(1)
            for pipeline_instance in self._get_group_pipelines(group):
                if pipeline_instance['name'] == matched_pipeline:
                    return True
            return False

        return name_like_in_group_filter
