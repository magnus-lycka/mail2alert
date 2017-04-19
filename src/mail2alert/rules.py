class Rule:
    def __init__(self, conf):
        self.owner = conf.get('owner', '')
        self.name = conf.get('name', '')
        self.filter = conf.get('filter', {})
        self.actions = conf.get('actions', [])

    def check(self, msg, functions):
        raise NotImplementedError

    def __str__(self):
        return '<%s: %s>' % (
            self.__class__.__name__,
            {x: y for x, y in self.__dict__.items() if y}
        )
