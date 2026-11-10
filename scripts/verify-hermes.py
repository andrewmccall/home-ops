#!/usr/bin/env python3
"""Verify the local Hermes port-forward, authentication, and one paid model response."""

import base64
import json
from pathlib import Path
import subprocess
import urllib.error
import urllib.request

import yaml


BASE = 'http://127.0.0.1:8642'


def main():
    with urllib.request.urlopen(BASE + '/health', timeout=10) as response:
        health = json.load(response)
    assert health.get('status') == 'ok' and health.get('platform') == 'hermes-agent', health
    print('PASS: Hermes health')

    model = yaml.safe_load((Path(__file__).resolve().parents[1] / 'cluster/apps/hermes/config.yaml').read_text())['model']
    body = json.dumps({'model': model['default'], 'messages': [{'role': 'user', 'content': 'Reply with exactly: hermes ready. Do not use any tools.'}], 'stream': False}).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(BASE + '/v1/chat/completions', data=body, headers={'Content-Type': 'application/json'}), timeout=10)
    except urllib.error.HTTPError as error:
        assert error.code == 401, f'Expected 401, got {error.code}'
    else:
        raise AssertionError('Unauthenticated model request succeeded')
    print('PASS: unauthenticated model request rejected')

    result = subprocess.run(['kubectl', '-n', 'hermes', 'get', 'secret', 'hermes-agent-api-keys', '-o', 'json'], check=True, capture_output=True)
    secret = json.loads(result.stdout)['data']
    key = base64.b64decode(secret['API_SERVER_KEY']).decode()
    request = urllib.request.Request(BASE + '/v1/chat/completions', data=body, headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
    with urllib.request.urlopen(request, timeout=180) as response:
        payload = json.load(response)
    content = payload['choices'][0]['message']['content']
    assert isinstance(content, str) and content.strip().lower().rstrip('.') == 'hermes ready', 'Model did not return the requested readiness response'
    print(f"PASS: authenticated Hermes model response from {model['provider']} {model['default']}")


if __name__ == '__main__':
    main()
