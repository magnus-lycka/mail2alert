import asyncio
import logging
import re
from collections import defaultdict
from enum import Enum, auto
from itertools import product
from xml.etree import ElementTree as Et

import aiohttp

from mail2alert.plugin import mail
from mail2alert.rules import Rule
from mail2alert.common import AlertLevels


async def get_json_url(session, url):
    logging.debug('Fetching url %s', url)
    with aiohttp.Timeout(10, loop=session.loop):
        async with session.get(url) as response:
            if response.status == 200:
                logging.debug(response)
                return await response.json()
            else:
                logging.error(response)


async def get_xml_url(session, url):
    logging.debug('Fetching url %s', url)
    with aiohttp.Timeout(10, loop=session.loop):
        async with session.get(url) as response:
            if response.status == 200:
                logging.debug(response)
                text = await response.text()
                return Et.fromstring(text)
            else:
                logging.error(response)


class Manager(mail.Manager):
    """
    gocd.Manager objects are handed mail messages.

    Based on the mail2alert configuration and knowledge about the
    GoCD server configuration, they determine what to do with the
    mail message.
    """

    def __init__(self, conf):
        super().__init__(conf)
        self._pipeline_groups = None
        self._pipeline_groups_time = 0
        # None is a valid value. I use NotImplemented as not set.
        self._auth = NotImplemented
        self.previous_pipeline_state = defaultdict(BuildStateUnknown)

    async def async_init(self):
        await self.fetch_cctray()

    @property
    def pipeline_groups_timeout(self):
        return self._pipeline_groups_time + 30

    @property
    async def pipeline_groups(self):
        if asyncio.get_event_loop().time() > self.pipeline_groups_timeout:
            # We can probably survive that subsequent requests use old
            # config while fetch is in progress.
            self._pipeline_groups_time = asyncio.get_event_loop().time()
            await self.fetch_pipeline_groups()
        return self._pipeline_groups

    @property
    async def rule_funcs(self):
        return {'pipelines': Pipelines(await self.pipeline_groups)}

    @staticmethod
    def rules(rule_list):
        for rule in rule_list:
            yield GocdRule(rule)

    @property
    def auth(self):
        if self._auth is NotImplemented:
            if 'user' in self.conf:
                self._auth = aiohttp.BasicAuth(
                    self.conf['user'],
                    self.conf['passwd']
                )
            else:
                self._auth = None
                logging.warning('Missing user in configuration')
        return self._auth

    async def fetch_pipeline_groups(self):
        try:
            logging.info('Fetching pipeline groups')
            async with aiohttp.ClientSession(auth=self.auth) as session:
                if 'url' not in self.conf:
                    error = "No URL in config, can't fetch pipeline groups"
                    logging.error(error)
                    logging.error(self.conf)
                    raise ValueError(error)
                base_url = self.conf['url']
                url = base_url + '/api/config/pipeline_groups'
                pipeline_groups = await get_json_url(session, url)
                if pipeline_groups:
                    self._pipeline_groups = pipeline_groups
                    logging.debug(
                        'Set pipeline groups config with %s pipeline groups.',
                        len(pipeline_groups)
                    )
                else:
                    logging.warning('Unable to fetch pipeline groups config.')
        except Exception as error:
            logging.exception('Exception in fetch_pipeline_groups: %s', error)

    async def fetch_cctray(self):
        try:
            logging.info('Fetching cctray')
            async with aiohttp.ClientSession(auth=self.auth) as session:
                if 'url' not in self.conf:
                    error = "No URL in config, can't fetch cctray"
                    logging.error(error)
                    logging.error(self.conf)
                    raise ValueError(error)
                base_url = self.conf['url']
                url = base_url + '/cctray.xml'
                tree = await get_xml_url(session, url)
                if tree:
                    self.parse_cctray(tree)
                else:
                    logging.warning('Unable to fetch cctray.')
        except Exception as error:
            logging.exception('Exception in fetch_cctray: %s', error)

    def parse_cctray(self, tree):
        when = defaultdict(str)
        for project in tree.findall('Project'):
            name_parts = [n.strip() for n in project.attrib['name'].split('::')]
            if len(name_parts) > 2:
                # Never mind job level
                continue
            pipeline_name = name_parts[0]
            stage_name = name_parts[1]
            timestamp = project.attrib['lastBuildTime']
            what = "{}/{}".format(pipeline_name, stage_name)
            if timestamp > when[pipeline_name]:
                state = build_state_factory(last_build_status=project.attrib['lastBuildStatus'])
                self.previous_pipeline_state[what] = state
                when[what] = timestamp
                logging.debug('Set state for %s to %s', what, state)

    @property
    async def rule_funcs(self):
        return {'pipelines': Pipelines(await self.pipeline_groups)}

    # noinspection PyMethodOverriding
    def get_message(self, content):
        return Message(content, previous_states=self.previous_pipeline_state)

    async def test(self):
        """
        This method can be used both to check that the configuration
        is correct, and to produce a report about where alerts go.
        """
        report = []
        pipeline_map = {}
        for pipeline_group in await self.pipeline_groups:
            group_report = {
                'pipeline_group': pipeline_group['name'],
                'pipelines': [
                    {'pipeline': p['name']}
                    for p in pipeline_group['pipelines']
                ]
            }
            report.append(group_report)
            for pipeline_report in group_report['pipelines']:
                pipeline_map[pipeline_report['pipeline']] = pipeline_report

        for msg in await self.test_msgs():
            for rule in self.rules(self.conf['rules']):
                if rule.check(
                    msg,
                    {'pipelines': Pipelines(await self.pipeline_groups)}
                ):
                    logging.debug('msg %s checks for rule %s' % (msg, rule))
                    self.add_alert_to_report(msg, rule, pipeline_map)
        return report

    async def test_msgs(self):
        pipelines = []
        for grp in await self.pipeline_groups:
            pipelines.extend([p['name'] for p in grp['pipelines']])
        return (
            dict(pipeline=p, event=e) for p, e in product(pipelines, Event)
        )

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
        Extract which pipeline and which event from the msg,
        and test with the filter
        """
        if 'events' in self.filter:
            if not msg['event']:
                logging.warning('No event found in %s' % msg)
                return []
            if not msg['event'] or not msg['event'].name in self.filter['events']:
                logging.debug('No match for %s', msg['event'])
                return []
            else:
                logging.debug('Match for %s', msg['event'])
        else:
            logging.warning('No event in rule %s.', self.filter)
        key, method = self.filter['function'].split('.')
        rule_filter = getattr(functions[key], method)(
            *tuple(self.filter.get('args', ()))
        )
        logging.debug('Filter %s' % rule_filter)
        if rule_filter(msg):
            logging.debug('Rule match, actions: %s', self.actions)
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


class BuildState:
    def __eq__(self, other):
        return self.__class__ == other.__class__


class BuildStateSuccess(BuildState):
    @staticmethod
    def after(old_state):
        return {
            BuildStateSuccess: Event.PASSES,
            BuildStateFailure: Event.FIXED,
            BuildStateUnknown: Event.FIXED,
        }[old_state.__class__]


class BuildStateFailure(BuildState):
    @staticmethod
    def after(old_state):
        return {
            BuildStateSuccess: Event.BREAKS,
            BuildStateFailure: Event.FAILS,
            BuildStateUnknown: Event.BREAKS,
        }[old_state.__class__]


class BuildStateUnknown(BuildState):
    @staticmethod
    def after(old_state):
        pass


def build_state_factory(*, event=None, last_build_status=None):
    if event:
        state = {
            Event.PASSES: BuildStateSuccess,
            Event.FIXED: BuildStateSuccess,
            Event.BREAKS: BuildStateFailure,
            Event.FAILS: BuildStateFailure,
            Event.CANCELLED: BuildStateUnknown,
        }[event]
    elif last_build_status:
        state = {
            'Success': BuildStateSuccess,
            'Failure': BuildStateFailure,
        }[last_build_status]
    else:
        raise ValueError('Need either event or last_builld_status')
    if state:
        return state()


class Pipelines:
    """
    This class should be passed the content from
    go/api/config/pipeline_groups
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
    def any():
        return lambda msg: True

    all = any  # For backwards compatibility. Deprecated.

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


class Message(mail.Message):
    event_map = {
        'is fixed': Event.FIXED,
        'is broken': Event.BREAKS,
        'is cancelled': Event.CANCELLED,
        'passed': Event.PASSES,
        'failed': Event.FAILS,
    }
    pattern = re.compile(r'Stage \[([^/]+)/[^/]+/([^/]+)/[^/]+\] (.+)$')

    def __init__(self, content, previous_states=None):
        if previous_states is None:
            previous_states = defaultdict(BuildStateUnknown)
        super().__init__(content)
        mo = self.pattern.search(self['Subject'])

        if not mo:
            logging.warning('Unable to parse message: %r' % content)
            self['pipeline'] = None
            self['event'] = None
            return

        self['pipeline'] = mo.group(1)
        stage = mo.group(2)
        event = self.event_map.get(mo.group(3).strip())

        if not event:
            logging.warning('No event found in %r', content)
            self['event'] = None
            return

        logging.debug('Got %s' % event)

        pipeline_stage = "{}/{}".format(self['pipeline'], stage)
        expected_event = build_state_factory(event=event).after(previous_states[pipeline_stage])
        if previous_states[pipeline_stage] == BuildStateUnknown():
            pass
        elif expected_event == event:
            pass
        elif expected_event in (Event.FIXED, Event.BREAKS):
            logging.warning(
                'Got %s instead of %s expected due to history. Changing!',
                event,
                expected_event
            )
            event = expected_event
        else:
            logging.warning(
                'Got %s instead of %s expected due to history. Keep that!',
                event,
                expected_event
            )

        self['event'] = event

        if event:
            previous_states[pipeline_stage] = build_state_factory(event=event)
            self.set_alert_level()

    def set_alert_level(self):
        if self['event'] in (Event.BREAKS, Event.FAILS):
            self.alert_level = AlertLevels.DANGER
        elif self['event'] in (Event.PASSES, Event.FIXED):
            self.alert_level = AlertLevels.SUCCESS
        elif self['event'] == Event.CANCELLED:
            self.alert_level = AlertLevels.WARNING
