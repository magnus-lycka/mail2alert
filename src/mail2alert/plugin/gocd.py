import asyncio
import logging
import re
from enum import Enum, auto
from itertools import product

import aiohttp

from mail2alert.plugin import mail
from ..actions import Actions
from ..rules import Rule


async def fetch(session, url):
    logging.debug('Fetching url %s' % url)
    with aiohttp.Timeout(10, loop=session.loop):
        async with session.get(url) as response:
            if response.status == 200:
                logging.debug(response)
                return await response.json()
            else:
                logging.error(response)


class Manager:
    """
    gocd.Manager objects are handed mail messages.

    Based on the mail2alert configuration and knowledge about the
    GoCD server configuration, they determine what to do with the
    mail message.
    """

    def __init__(self, conf):
        logging.info('Started {}'.format(self.__class__))
        self.conf = conf
        self.pipeline_groups = []
        coro = self.fetch_pipeline_groups()
        asyncio.ensure_future(coro)

    @property
    def rule_funcs(self):
        return {'pipelines': Pipelines(self.pipeline_groups)}

    @staticmethod
    def rules(rule_list):
        for rule in rule_list:
            yield GocdRule(rule)

    async def fetch_pipeline_groups(self, loop=None):
        logging.info('Fetching pipeline groups')
        loop = loop or asyncio.get_event_loop()
        while True:
            try:
                if 'user' in self.conf:
                    auth = aiohttp.BasicAuth(self.conf['user'], self.conf['passwd'])
                else:
                    auth = None
                    logging.warning('Missing user in configuration')
                async with aiohttp.ClientSession(
                    loop=loop,
                    auth=auth
                ) as session:
                    if 'url' not in self.conf:
                        logging.error("No URL in config, can't fetch pipeline groups")
                        logging.error(self.conf)
                        return
                    base_url = self.conf['url']
                    url = base_url + '/api/config/pipeline_groups'
                    pipeline_groups = await fetch(session, url)
                    if pipeline_groups:
                        self.pipeline_groups = pipeline_groups
                        logging.debug('Set pipeline groups config with {} pipeline groups.'.format(
                            len(self.pipeline_groups))
                        )
                    else:
                        logging.warning('Unable to fetch pipeline groups config.')
            except Exception as error:
                logging.exception('Exception in fetch_pipeline_groups: %s', error)
            await asyncio.sleep(30)

    def wants_message(self, mail_from, rcpt_tos, content):
        """
        Determine whether the manager is interested in a certain message.
        """
        wanted = self.conf['messages-we-want']
        wanted_to = wanted.get('to')
        wanted_from = wanted.get('from')
        logging.debug('We vant to: {} or from: {}'.format(wanted_to, wanted_from))
        logging.debug('We got to: {} and from: {}'.format(rcpt_tos, mail_from))
        if wanted_to:
            return wanted_to in rcpt_tos
        if wanted_from:
            return wanted_from == mail_from

    def process_message(self, mail_from, rcpt_tos, binary_content):
        logging.debug('process_message("{}", {}, {})'.format(mail_from, rcpt_tos, binary_content))
        recipients = []
        msg = Message(binary_content)
        logging.debug('Extracted message %s' % msg)
        for rule in self.rules(self.conf['rules']):
            logging.debug('Check %s' % rule)
            rule_funcs = {
                'pipelines': Pipelines(self.pipeline_groups),
            }
            actions = Actions(rule.check(msg, rule_funcs))
            recipients.extend(actions.mailto)
        return mail_from, recipients, binary_content

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
            for rule in self.rules(self.conf['rules']):
                if rule.check(msg, {'pipelines': Pipelines(self.pipeline_groups)}):
                    logging.debug('msg %s checks for rule %s' % (msg, rule))
                    self.add_alert_to_report(msg, rule, pipeline_map)
        return report

    def test_msgs(self):
        pipelines = []
        for grp in self.pipeline_groups:
            pipelines.extend([p['name'] for p in grp['pipelines']])
        return (dict(pipeline=p, event=e) for p, e in product(pipelines, Event))

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
        if msg['event'].name not in alert['events']:
            alert['events'].append(msg['event'].name)


class GocdRule(Rule):
    def check(self, msg, functions):
        """
        Extract which pipeline and which event from the msg, and test with the filter
        """
        if 'events' in self.filter:
            if not msg['event']:
                logging.warning('No event found in %s' % msg)
                return []
            if not msg['event'] or not msg['event'].name in self.filter['events']:
                logging.debug('No match for %s' % msg['event'])
                return []
            else:
                logging.debug('Match for %s' % msg['event'])
        else:
            logging.warning('No event in rule %s.' % self.filter)
        key, method = self.filter['function'].split('.')
        rule_filter = getattr(functions[key], method)(*tuple(self.filter.get('args', ())))
        logging.debug('Filter %s' % rule_filter)
        if rule_filter(msg):
            logging.debug('Rule match, actions: %s' % self.actions)
            return self.actions
        return []


class Event(Enum):
    BREAKS = auto()
    CANCELLED = auto()
    FAILS = auto()
    FIXED = auto()
    PASSES = auto()

    @classmethod
    def names(cls):
        return list(cls.__members__.keys())


class Message(mail.Message):
    def __init__(self, content):
        super().__init__(content)
        event_map = {
            'is fixed': Event.FIXED,
            'is broken': Event.BREAKS,
            'is cancelled': Event.CANCELLED,
            'passed': Event.PASSES,
            'failed': Event.FAILS,
        }
        pattern = re.compile(r'Stage \[([^/]+)/[^/]+/[^/]+/[^/]+\] (.+)$')
        mo = pattern.search(self['subject'])
        if mo:
            event = event_map.get(mo.group(2).strip())
            if not event:
                logging.warning('Unexpected event "%s" in %r' % (mo.group(2), content))
            else:
                logging.debug('Got %s' % event)
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
        else:
            return []

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
