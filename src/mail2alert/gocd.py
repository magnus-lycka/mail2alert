"""
Process objects are handed mail messages.
"""


class Manager:
    def __init__(self, conf):
        self.conf = conf
        self.go_config_mod_time = None
        self.pipeline_groups = []

    def read_message(self, mailfrom, rcpttos, data):
        self.mailfrom = mailfrom
        self.rcpttos = rcpttos
        self.data = data

    def wants_message(self):
        for rcpt in self.rcpttos:
            if 'gocdnotifications' in rcpt:
                return True
        else:
            return False

    def process(self):
        return self.mailfrom, ['magnus.lycka@pagero.com'], self.data


# Check periodically whether go_config_mod_time changed
# If it did, get a list of pipeline groups and pipelines in each
# Go through the pipelines and update our knowledge of alert rules
# If a pipeline didn't have alert rules, give it default alert rules.


class PipelineGroup:
    def __init__(self):
        self.name = ''
        self.default_alert = None
        self.pipelines = []


class Pipeline:
    def __init__(self):
        self.name = ''
        self.alerts = []


class Alert:
    def __init__(self, event, action):
        self.event = self.event_filter(event)
        self.action = action

    @staticmethod
    def event_filter(string):
        for candidate in (
            'all',
            'passes',
            'fails',
            'breaks',
            'fixed',
            'cancelled',
            'nodefault',
        ):
            if string.upper().startswith('MAIL2ALERT_' + candidate.upper()):
                return candidate
        raise ValueError('{} is not a recognized alert event'.format(string))


'''
import aiohttp
async def get_content(url):
     response = await aiohttp.get(url)
     return (await response.text())


import asyncio
loop = asyncio.get_event_loop()
content = loop.run_until_complete(
   get_content('http://knowpapa.com')
)
print(content)
'''


