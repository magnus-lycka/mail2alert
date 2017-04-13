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
        for pipeline
        return []


class GocdRule(Rule):
    def check(self, msg, functions):
        """
        Extract which pipeline and which event from the msg, and test with the filter
        """
        if not msg['event'] in self.filter['events']:
            return []
        key, method = self.filter['function'].split('.')
        filter = getattr(functions[key], method)(*tuple(self.filter['args']))
        if filter(msg):
            return self.actions
        return []


def get_rules(rule_list):
    for rule in rule_list:
        yield GocdRule(**rule)


class Message(dict):
    def __init__(self, content):
        self['event'] = None
        self['pipeline'] = None


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
