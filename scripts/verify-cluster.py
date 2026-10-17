#!/usr/bin/env python3
"""Render Flux entry points and verify DNS and Sandbox configuration. Requires PyYAML and jsonschema."""

import json
from pathlib import Path
import subprocess
import sys

import yaml
from jsonschema import Draft4Validator


ROOT = Path(__file__).resolve().parents[1]
DOMAIN = 'cluster.andrewmccall.com'


def close_structural_objects(schema):
    """Reject fields Kubernetes would prune from structured CRD objects."""
    if isinstance(schema, dict):
        for value in list(schema.values()):
            close_structural_objects(value)
        if schema.get('type') == 'object' and schema.get('properties') and 'additionalProperties' not in schema and not schema.get('x-kubernetes-preserve-unknown-fields'):
            schema['additionalProperties'] = False
    elif isinstance(schema, list):
        for value in schema:
            close_structural_objects(value)


def main():
    rendered = {}
    for name in ('flux-system', 'flux-system/flux-system', 'base', 'core', 'core/agent-sandbox', 'crds', 'apps'):
        result = subprocess.run(['kubectl', 'kustomize', str(ROOT / 'cluster' / name)], check=True, capture_output=True, text=True)
        documents = [doc for doc in yaml.safe_load_all(result.stdout) if doc]
        for doc in documents:
            if 'cluster.local' in json.dumps(doc):
                raise ValueError(f'{name}: {doc["kind"]}/{doc["metadata"]["name"]} contains cluster.local')
        rendered[name] = documents
        print(f'PASS: cluster/{name} renders without cluster.local')

    flux = rendered['flux-system/flux-system']
    base = next(d for d in rendered['flux-system'] if d['kind'] == 'Kustomization' and d['metadata']['name'] == 'base')
    assert base['spec']['path'] == './cluster/base'
    assert base['spec']['decryption']['secretRef']['name'] == 'sops-age'
    for name in ('source-controller', 'kustomize-controller', 'helm-controller'):
        deployment = next(d for d in flux if d['kind'] == 'Deployment' and d['metadata']['name'] == name)
        args = deployment['spec']['template']['spec']['containers'][0]['args']
        expected = f'--events-addr=http://notification-controller.$(RUNTIME_NAMESPACE).svc.{DOMAIN}./'
        assert expected in args, f'{name}: incorrect event address'
        if name == 'source-controller':
            assert f'--storage-adv-addr=source-controller.$(RUNTIME_NAMESPACE).svc.{DOMAIN}.' in args

    apps = rendered['apps']
    assert not any(d['kind'] == 'OpenClawInstance' for d in apps), 'OpenClaw still rendered'
    assert not any(d['kind'] == 'HelmRelease' and d['metadata']['name'] == 'openclaw-operator' for d in apps)
    sandbox = next(d for d in apps if d['kind'] == 'Sandbox' and d['metadata']['name'] == 'hermes')
    crd = next(d for d in rendered['crds'] if d['kind'] == 'CustomResourceDefinition' and d['metadata']['name'] == 'sandboxes.agents.x-k8s.io')
    version = next(v for v in crd['spec']['versions'] if v['name'] == sandbox['apiVersion'].split('/')[1])
    schema = version['schema']['openAPIV3Schema']
    close_structural_objects(schema)
    Draft4Validator(schema).validate(sandbox)
    pod = sandbox['spec']['podTemplate']['spec']
    assert pod['automountServiceAccountToken'] is False
    container = pod['containers'][0]
    assert '@sha256:' in container['image'], 'Hermes image must be pinned'
    refs = {e['name']: e['valueFrom']['secretKeyRef']['key'] for e in container['env'] if 'valueFrom' in e}
    assert refs == {'OPENROUTER_API_KEY': 'OPENROUTER_API_KEY', 'API_SERVER_KEY': 'API_SERVER_KEY'}
    assert sandbox['spec']['volumeClaimTemplates'][0]['spec']['storageClassName'] == 'longhorn'
    app_kustomization = next(d for d in rendered['base'] if d['kind'] == 'Kustomization' and d['metadata']['name'] == 'apps')
    assert {'name': 'agent-sandbox'} in app_kustomization['spec']['dependsOn']
    print('PASS: Hermes CRD schema, credential references, persistent storage and controller ordering')


if __name__ == '__main__':
    try:
        main()
    except (AssertionError, ValueError, subprocess.CalledProcessError) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError):
            print(error.stderr, file=sys.stderr)
        sys.exit(1)
