import logging


class Rule:
    def __init__(self, conf):
        self.owner = conf.get('owner', '')
        self.name = conf.get('name', '')
        self.filter = conf.get('filter', {})
        self.actions = conf.get('actions', [])

    def check(self, msg, functions):
        raise NotImplementedError  # pragma: no cover

    def __str__(self):
        return '<%s: %s>' % (
            self.__class__.__name__,
            {x: y for x, y in self.__dict__.items() if y}
        )

    def check(self, msg, functions):
        """
        Extract data from the msg, and test with the filter
        """
        key, method = self.filter['function'].split('.')
        rule_filter = getattr(functions[key], method)(*tuple(self.filter.get('args', ())))
        logging.debug('Filter %s' % rule_filter)
        if rule_filter(msg):
            logging.debug('Rule match, actions: %s' % self.actions)
            return self.actions
        return []
