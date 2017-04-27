import yaml

def add_rules(receiver, pipelinegroups):
    rules = []
    for group in pipelinegroups:
        rule1 = {
            'actions': ['mailto:%s.example.com' % receiver],
            'filter': {
                'events': ['FIXES', 'BREAKS'],
                'function': 'pipelines.in_group',
                'args': [group]
            }
        }
        rules.append(rule1)
        rule2 = {
            'actions': ['mailto:%s.example.com' % receiver],
            'filter': {
                'events': ['FIXES', 'BREAKS'],
                'function': 'pipelines.in_group',
                'args': [r'(.+)-release.*', group]
            }
        }
        rules.append(rule2)
    return rules

def main():
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
