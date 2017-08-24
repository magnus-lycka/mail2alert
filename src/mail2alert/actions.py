import logging


class Actions:
    def __init__(self, target_strings):
        self.mailto = []
        self.slack = []
        for text in target_strings:
            kind, what = text.split(':')
            if kind == 'mailto':
                self.mailto.append(what)
            elif kind == 'slack':
                self.slack.append(what)
            else:
                logging.error('Unexpected action: ' + text)
