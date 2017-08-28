import logging


class Actions:
    _action_types = {}

    @classmethod
    def add_action_type(cls, action_type):
        cls._action_types[action_type.kind()] = action_type

    def __init__(self, target_strings):
        self._actions = {kind: [] for kind in self._action_types}
        for text in target_strings:
            kind, *args = text.split(':')
            try:
                action_type = self._action_types[kind]
                self._actions[action_type.kind()].append(action_type(*args))
            except KeyError:
                logging.error('Unexpected action: ' + text)

    def __getattr__(self, item):
        return self._actions[item]


class Action:
    def __init__(self, destination, *args):
        self.destination = destination

    @classmethod
    def kind(cls):
        return cls.__name__.lower()


class Mailto(Action):
    pass


Actions.add_action_type(Mailto)


class Slack(Action):
    def __init__(self, destination, style='brief'):
        super().__init__(destination)
        self.style = style


Actions.add_action_type(Slack)
