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
    assert refs == {**{key: key for key in ('ANTHROPIC_API_KEY', 'API_SERVER_KEY', 'HOME_ASSISTANT_TOKEN',
                                            'SPROOZI_TASK_TOKEN', 'ALERTMANAGER_WEBHOOK_TOKEN', 'TELEGRAM_BOT_TOKEN')},
                    'TELEGRAM_ALLOWED_USERS': 'TELEGRAM_USER_ID', 'TELEGRAM_HOME_CHANNEL': 'TELEGRAM_USER_ID'}
    assert sandbox['spec']['volumeClaimTemplates'][0]['spec']['storageClassName'] == 'longhorn'
    service = next(d for d in apps if d['kind'] == 'Service' and d['metadata']['name'] == 'hermes-api')
    assert service['spec']['selector'] == {'app.kubernetes.io/name': 'hermes'}
    assert service['spec']['ports'] == [{'name': 'api', 'port': 8642, 'targetPort': 'api'}]
    home_assistant = next(d for d in apps if d['kind'] == 'HelmRelease' and d['metadata']['name'] == 'home-assistant')
    ha_values = home_assistant['spec']['values']
    assert ha_values['controllers']['home-assistant']['containers']['app']['env']['OPENAI_BASE_URL'] == 'http://hermes-api.hermes.svc:8642/v1'
    for volume, settings in ha_values['persistence'].items():
        for controller, mounts in settings.get('advancedMounts', {}).items():
            assert controller in ha_values['controllers'], f'{volume}: unknown controller {controller}'
            for target in mounts:
                assert target in ha_values['controllers'][controller]['containers'], f'{volume}: unknown container {target}'
    # Settings Git pins (Hermes's managed scope); the seed is Hermes's first-start default.
    managed_map = next(d for d in apps if d['kind'] == 'ConfigMap' and d['metadata']['name'] == 'hermes-managed')
    hermes_config = yaml.safe_load(managed_map['data']['config.yaml'])
    seed = next(d for d in apps if d['kind'] == 'ConfigMap' and d['metadata']['name'] == 'hermes-seed')
    assert seed['data']['SOUL.md'].startswith('You are Ada'), "Hermes's identity seed must name Ada"
    assert seed['metadata']['annotations']['kustomize.toolkit.fluxcd.io/substitute'] == 'disabled'
    assert 'model' in yaml.safe_load(seed['data']['config.yaml']) and 'model' not in hermes_config, 'Hermes owns its model'
    mounts = {m['mountPath']: m['name'] for m in container['volumeMounts']}
    assert mounts.get('/etc/hermes') == 'managed' and all(m.get('readOnly') for m in container['volumeMounts'] if m['name'] == 'managed'), 'Managed scope must be read-only at /etc/hermes'
    assert hermes_config['platform_toolsets']['api_server'] == ['home_assistant']
    mcp = hermes_config['mcp_servers']['home_assistant']
    assert mcp['url'] == 'http://home-assistant-app.house.svc:8123/api/mcp'
    assert mcp['headers']['Authorization'] == 'Bearer $${HOME_ASSISTANT_TOKEN}', 'MCP credential reference must survive Flux substitution'
    policy = next(d for d in apps if d['kind'] == 'NetworkPolicy' and d['metadata']['name'] == 'hermes')
    assert policy['spec']['ingress'] == [{
        'from': [{
            'namespaceSelector': {'matchLabels': {'kubernetes.io/metadata.name': 'house'}},
            'podSelector': {'matchLabels': {'app.kubernetes.io/instance': 'home-assistant', 'app.kubernetes.io/controller': 'home-assistant'}},
        }],
        'ports': [{'protocol': 'TCP', 'port': 8642}],
    }]
    assert {
        'to': [{
            'namespaceSelector': {'matchLabels': {'kubernetes.io/metadata.name': 'house'}},
            'podSelector': {'matchLabels': {'app.kubernetes.io/instance': 'home-assistant', 'app.kubernetes.io/controller': 'home-assistant'}},
        }],
        'ports': [{'protocol': 'TCP', 'port': 8123}],
    } in policy['spec']['egress'], 'Hermes cannot reach the Home Assistant MCP server'
    tasks_mcp = hermes_config['mcp_servers']['sproozi-tasks']
    assert tasks_mcp['url'] == 'https://sproozi-tasks.sproozi-system.svc:8443/mcp'
    assert tasks_mcp['headers']['Authorization'] == 'Bearer $${SPROOZI_TASK_TOKEN}', 'Task credential reference must survive Flux substitution'
    task_mcp = {'namespaceSelector': {'matchLabels': {'kubernetes.io/metadata.name': 'sproozi-system'}},
                'podSelector': {'matchLabels': {'app.kubernetes.io/component': 'task-mcp'}}}
    assert {'to': [task_mcp], 'ports': [{'protocol': 'TCP', 'port': 8443}]} in policy['spec']['egress'], 'Hermes cannot reach the Sproozi task service'
    tasks = next(d for d in apps if d['kind'] == 'Deployment' and d['metadata']['name'] == 'sproozi-tasks')
    assert tasks['spec']['template']['metadata']['labels']['app.kubernetes.io/component'] == 'task-mcp'
    tasks_policy = next(d for d in apps if d['kind'] == 'NetworkPolicy' and d['metadata']['name'] == 'sproozi-tasks')
    assert tasks_policy['spec']['ingress'] == [{'from': [{
        'namespaceSelector': {'matchLabels': {'kubernetes.io/metadata.name': 'hermes'}},
        'podSelector': {'matchLabels': {'app.kubernetes.io/name': 'hermes'}}}],
        'ports': [{'protocol': 'TCP', 'port': 8443}]}], 'Only Hermes may call the Sproozi task service'
    tasks_config = next(d for d in apps if d['kind'] == 'ConfigMap' and d['metadata']['name'].startswith('sproozi-tasks-'))
    for workflow in json.loads(tasks_config['data']['tasks.json'])['workflows'].values():
        assert any(d['kind'] == 'AgentTemplate' and d['metadata']['name'] == workflow['template'] for d in apps), f'{workflow["template"]}: no AgentTemplate'
    print('PASS: Hermes reaches only the Sproozi task service, whose workflows name existing templates')
    route = hermes_config['platforms']['webhook']['extra']['routes']['alertmanager']
    assert route['secret'] == '$${ALERTMANAGER_WEBHOOK_TOKEN}', 'Webhook secret reference must survive Flux substitution'
    assert hermes_config['platform_toolsets']['webhook'] == ['hermes-webhook', 'sproozi-tasks'], 'Alert payloads must not reach Home Assistant or the terminal'
    sre = next(d for d in apps if d['kind'] == 'ConfigMap' and d['metadata']['name'] == 'hermes-sre')
    assert sre['metadata']['annotations']['kustomize.toolkit.fluxcd.io/substitute'] == 'disabled'
    assert route['script'] in sre['data'] and set(route['skills']) == {'sre-alerts'}
    stack = next(d for d in apps if d['kind'] == 'HelmRelease' and d['metadata']['name'] == 'kube-prometheus-stack')['spec']['values']['alertmanager']
    receiver = next(r for r in stack['config']['receivers'] if r['name'] == 'hermes')['webhook_configs'][0]
    assert receiver['url'] == 'http://hermes-webhook.hermes.svc:8644/webhooks/alertmanager'
    secret_file = receiver['http_config']['http_headers']['X-Gitlab-Token']['files'][0]
    assert secret_file.split('/')[4] in stack['alertmanagerSpec']['secrets'], 'Alertmanager does not mount the webhook token'
    webhook_policy = next(d for d in apps if d['kind'] == 'NetworkPolicy' and d['metadata']['name'] == 'hermes-alertmanager')
    assert webhook_policy['spec']['ingress'][0]['ports'] == [{'protocol': 'TCP', 'port': 8644}]
    print('PASS: Alertmanager reaches the authenticated Hermes webhook route, whose tools exclude Home Assistant')
    app_kustomization = next(d for d in rendered['base'] if d['kind'] == 'Kustomization' and d['metadata']['name'] == 'apps')
    assert {'name': 'agent-sandbox'} in app_kustomization['spec']['dependsOn']
    print('PASS: Hermes CRD schema, credential references, persistent storage and controller ordering')
    print('PASS: Home Assistant endpoint, Hermes API Service and scoped voice ingress')
    print('PASS: Voice cache mount targets and scoped Home Assistant MCP configuration')


if __name__ == '__main__':
    try:
        main()
    except (AssertionError, ValueError, subprocess.CalledProcessError) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError):
            print(error.stderr, file=sys.stderr)
        sys.exit(1)
