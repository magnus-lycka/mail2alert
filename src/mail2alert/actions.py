import logging

class Actions:
    def __init__(self, target_strings):
        self.mailto = []
        for text in target_strings:
            kind, what = text.split(':')
            if kind == 'mailto':
                self.mailto.append(what)
            else:
                logging.error('Unexpected action: ' + text)

