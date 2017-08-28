import logging


class Actions:
    def __init__(self, target_strings):
        self.mailto = []
        self.slack = []
        for text in target_strings:
            kind, *args = text.split(':')
            if kind == 'mailto':
                self.mailto.append(args[0])
            elif kind == 'slack':
                self.slack.append(args)
            else:
                logging.error('Unexpected action: ' + text)
