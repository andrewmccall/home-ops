#!/usr/bin/env python3
"""Remove legacy manual Home Assistant proxy overrides after the Helm upgrade."""

import copy
import json
import subprocess

import yaml


def without_proxy(template):
    template = copy.deepcopy(template)
    spec = template['spec']

    def keep(obj, field, predicate):
        if field in obj:
            values = [value for value in obj[field] if predicate(value)]
            if values:
                obj[field] = values
            else:
                del obj[field]

    for alias in spec.get('hostAliases', []):
        alias['hostnames'] = [name for name in alias['hostnames'] if name != 'api.openai.com']
    keep(spec, 'hostAliases', lambda alias: bool(alias['hostnames']))
    keep(spec, 'initContainers', lambda container: container['name'] != 'init-merge-openai-ca')
    old_volumes = {'openai-ca', 'ca-bundle-workdir'}
    keep(spec, 'volumes', lambda volume: volume['name'] not in old_volumes)
    for container in spec.get('containers', []) + spec.get('initContainers', []):
        keep(container, 'volumeMounts', lambda mount: mount['name'] not in old_volumes)
        keep(container, 'env', lambda env: not (env['name'] == 'REQUESTS_CA_BUNDLE' and env.get('value') == '/work/combined-ca.pem'))
    return template


def main():
    manifest = subprocess.run(['helm', 'get', 'manifest', 'home-assistant', '-n', 'house'], check=True, capture_output=True, text=True)
    desired = next(doc for doc in yaml.safe_load_all(manifest.stdout) if doc and doc.get('kind') == 'Deployment' and doc['metadata']['name'] == 'home-assistant')
    assert without_proxy(desired['spec']['template']) == desired['spec']['template'], 'Upgrade Helm to the proxy-free manifest before running this cleanup.'
    result = subprocess.run(['kubectl', '-n', 'house', 'get', 'deployment', 'home-assistant', '-o', 'json'], check=True, capture_output=True)
    deployment = json.loads(result.stdout)
    current = deployment['spec']['template']
    clean = without_proxy(current)
    if clean == current:
        print('Home Assistant has no legacy proxy overrides.')
        return
    patch = [{'op': 'test', 'path': '/spec/template', 'value': current}, {'op': 'replace', 'path': '/spec/template', 'value': clean}]
    subprocess.run(['kubectl', '-n', 'house', 'patch', 'deployment', 'home-assistant', '--type=json', '-p', json.dumps(patch)], check=True, capture_output=True)
    print('Removed legacy Home Assistant proxy overrides; Deployment rollout started.')


if __name__ == '__main__':
    main()
