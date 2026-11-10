#!/usr/bin/env python3
"""Mint a "Prometheus" Home Assistant token and save it as a SOPS Secret.

Prometheus uses it to scrape /api/prometheus (see the ServiceMonitor in
cluster/apps/house/home-assistant). The token stays in memory and is only
written encrypted. Encrypting needs just the public age recipient in .sops.yaml.

The named long-lived token belongs to the existing Home Assistant owner and
lasts ten years; revoke it under that owner's Security settings to retire it.
Delete the Secret file and the token before running this again.
"""

import json
from pathlib import Path
import subprocess

CLIENT_NAME = 'Prometheus'

# Executed inside Home Assistant, where its auth and websocket APIs are local.
PROVISION = r'''
import asyncio, json, urllib.parse, urllib.request
from pathlib import Path
import aiohttp
auth = json.loads(Path('/config/.storage/auth').read_text())['data']
if any(t.get('client_name') == CLIENT_NAME for t in auth['refresh_tokens']):
    raise RuntimeError(CLIENT_NAME + ' token exists but its Secret is missing. Revoke it in Home Assistant first.')
owners = {u['id'] for u in auth['users'] if u.get('is_owner') and u.get('is_active')}
refresh = next(t for t in auth['refresh_tokens'] if t['user_id'] in owners and t['token_type'] == 'normal' and t.get('client_id'))
form = urllib.parse.urlencode({'grant_type': 'refresh_token', 'refresh_token': refresh['token'], 'client_id': refresh['client_id']}).encode()
with urllib.request.urlopen('http://127.0.0.1:8123/auth/token', data=form, timeout=15) as r:
    access = json.load(r)['access_token']
async def main():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect('http://127.0.0.1:8123/api/websocket') as ws:
            await ws.receive_json(timeout=15)
            await ws.send_json({'type': 'auth', 'access_token': access})
            if (await ws.receive_json(timeout=15))['type'] != 'auth_ok':
                raise RuntimeError('Home Assistant authentication failed.')
            await ws.send_json({'id': 1, 'type': 'auth/long_lived_access_token', 'client_name': CLIENT_NAME, 'lifespan': 3650})
            result = await ws.receive_json(timeout=15)
            if not result.get('success'):
                raise RuntimeError('Home Assistant rejected token creation.')
            print(json.dumps({'token': result['result']}))
asyncio.run(main())
'''.replace('CLIENT_NAME', repr(CLIENT_NAME))


def main():
    root = Path(__file__).resolve().parents[1]
    target = root / 'cluster/apps/house/home-assistant/prometheus-token.sops.yaml'
    if target.exists():
        print(f'{target.relative_to(root)} already exists; retained it.')
        return
    result = subprocess.run(['kubectl', '-n', 'house', 'exec', 'deploy/home-assistant', '-c', 'app', '--', 'python3', '-c', PROVISION], check=True, capture_output=True)
    secret = {
        'apiVersion': 'v1',
        'kind': 'Secret',
        'metadata': {'name': 'home-assistant-prometheus-token', 'namespace': 'house'},
        'type': 'Opaque',
        'stringData': {'token': json.loads(result.stdout)['token']},
    }
    result = subprocess.run(['sops', '--encrypt', '--filename-override', str(target), '--input-type', 'json', '--output-type', 'yaml', '/dev/stdin'], input=json.dumps(secret).encode(), check=True, capture_output=True, cwd=root)
    target.write_bytes(result.stdout)
    print(f'Encrypted the {CLIENT_NAME} token into {target.relative_to(root)}. It expires after ten years.')


if __name__ == '__main__':
    main()
