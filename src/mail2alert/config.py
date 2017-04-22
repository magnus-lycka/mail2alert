import logging
import yaml
from os.path import expandvars
"""
Read configuration from YAML file and expand environment
variables in all values.
"""


class Configuration(dict):
    def __init__(self):
        super().__init__()
        with open('configuration.yml') as conf_file:
            data = yaml.load(conf_file)
            expand_vars(data)
            for key, value in data.items():
                self[key] = value
            logging.debug('read configuration from {}'.format(conf_file.name))
            logging.debug('got configuration {}'.format(self))


def expand_vars(structure):
    for key, value in structure.items():
        if isinstance(value, str):
            structure[key] = expandvars(value)
        elif isinstance(value, dict):
            expand_vars(value)
        elif isinstance(value, list):
            expand_list(value)


def expand_list(structure):
    for i, item in enumerate(structure):
        if isinstance(item, str):
            structure[i] = expandvars(item)
        elif isinstance(item, dict):
            expand_vars(item)
        elif isinstance(item, list):
            expand_list(item)
