import yaml
import argparse

"""
Example script for bulk generation of rules.
"""


def add_rules(receiver, pipelinegroups):
    mail_domain = 'example.com'
    rules = []
    for group in pipelinegroups:
        rule1 = {
            'actions': ['mailto:%s@%s' % (receiver, mail_domain)],
            'filter': {
                'events': ['FIXED', 'BREAKS'],
                'function': 'pipelines.in_group',
                'args': [group]
            }
        }
        rules.append(rule1)
        rule2 = {
            'actions': ['mailto:%s@%s' % (receiver, mail_domain)],
            'filter': {
                'events': ['FIXED', 'BREAKS'],
                'function': 'pipelines.name_like_in_group',
                'args': [r'(.+)-release.*', group]
            }
        }
        rules.append(rule2)
    return rules


def main():
    parser = argparse.ArgumentParser(description='Create rules config')
    parser.add_argument('-i', '--input', )
    rules = []
    with open('actions.yml') as actions:
        for receiver, pipelinegroups in yaml.load(actions).items():
            rules.extend(add_rules(receiver, pipelinegroups))
        with open('snippets.yaml', 'w') as snippet:
            yaml.dump(
                dict(managers=[dict(rules=rules)]),
                snippet
            )

if __name__ == '__main__':
    main()
