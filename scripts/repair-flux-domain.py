#!/usr/bin/env python3
"""Repair live Flux DNS arguments without changing controller versions."""

import argparse
import json
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Apply the repair; default is a server-side dry run.')
    options = parser.parse_args()
    for name in ('source-controller', 'kustomize-controller', 'helm-controller'):
        result = subprocess.run(['kubectl', '-n', 'flux-system', 'get', 'deployment', name, '-o', 'json'], check=True, capture_output=True)
        deployment = json.loads(result.stdout)
        patches = []
        for index, container in enumerate(deployment['spec']['template']['spec']['containers']):
            arguments = container.get('args', [])
            repaired = [arg.replace('.svc.cluster.local.', '.svc.cluster.andrewmccall.com.') for arg in arguments]
            if repaired != arguments:
                path = f'/spec/template/spec/containers/{index}/args'
                patches.extend([{'op': 'test', 'path': path, 'value': arguments}, {'op': 'replace', 'path': path, 'value': repaired}])
        if not patches:
            print(f'{name}: no cluster.local arguments to repair')
            continue
        command = ['kubectl', '-n', 'flux-system', 'patch', 'deployment', name, '--type=json', '-p', json.dumps(patches)]
        if not options.apply:
            command.append('--dry-run=server')
        subprocess.run(command, check=True, capture_output=True)
        action = 'repaired' if options.apply else 'repair validated, use --apply to change the deployment'
        print(f'{name}: {action}')


if __name__ == '__main__':
    main()
