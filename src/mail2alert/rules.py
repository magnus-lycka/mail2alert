class Rule:
    def __init__(self, conf):
        self.owner = conf.get('owner', '')
        self.name = conf.get('name', '')
        self.filter = conf.get('filter', {})
        self.actions = conf.get('actions', [])

    def check(self, msg):
        raise NotImplementedError
