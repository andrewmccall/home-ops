#!/usr/bin/env python3
"""Verify the local Hermes port-forward, authentication, and one paid model response."""

import base64
import json
import subprocess
import urllib.error
import urllib.request


BASE = 'http://127.0.0.1:8642'


def main():
    with urllib.request.urlopen(BASE + '/health', timeout=10) as response:
        health = json.load(response)
    assert health.get('status') == 'ok' and health.get('platform') == 'hermes-agent', health
    print('PASS: Hermes health')

    body = json.dumps({'model': 'google/gemini-3-flash-preview', 'messages': [{'role': 'user', 'content': 'Reply with exactly: hermes ready. Do not use any tools.'}], 'stream': False}).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(BASE + '/v1/chat/completions', data=body, headers={'Content-Type': 'application/json'}), timeout=10)
    except urllib.error.HTTPError as error:
        assert error.code == 401, f'Expected 401, got {error.code}'
    else:
        raise AssertionError('Unauthenticated model request succeeded')
    print('PASS: unauthenticated model request rejected')

    result = subprocess.run(['kubectl', '-n', 'hermes', 'get', 'secret', 'hermes-agent-api-keys', '-o', 'json'], check=True, capture_output=True)
    secret = json.loads(result.stdout)['data']
    assert 'OPENROUTER_API_KEY' in secret, 'New OpenRouter key has not been configured'
    key = base64.b64decode(secret['API_SERVER_KEY']).decode()
    request = urllib.request.Request(BASE + '/v1/chat/completions', data=body, headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
    with urllib.request.urlopen(request, timeout=180) as response:
        payload = json.load(response)
    content = payload['choices'][0]['message']['content']
    assert isinstance(content, str) and content.strip().lower().rstrip('.') == 'hermes ready', 'Model did not return the requested readiness response'
    print('PASS: authenticated Hermes model response through OpenRouter')


if __name__ == '__main__':
    main()
