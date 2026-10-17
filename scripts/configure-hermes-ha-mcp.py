#!/usr/bin/env python3
"""Save a dedicated Home Assistant MCP credential in Hermes' SOPS Secret.

Run with --cluster-age-key to use Flux's age identity. Tokens stay in memory.
The named long-lived token belongs to the existing Home Assistant owner; revoke
it under that owner's Security settings when retiring this integration.
"""

import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import tempfile


# Executed inside Home Assistant, where its supported auth/config APIs are local.
PROVISION = r'''
import asyncio, json, urllib.parse, urllib.request
from pathlib import Path
import aiohttp
storage = Path('/config/.storage')
entries = json.loads((storage / 'core.config_entries').read_text())['data']['entries']
servers = [e for e in entries if e['domain'] == 'mcp_server' and not e.get('disabled_by')]
if len(servers) != 1 or servers[0]['data'].get('all_llm_apis') or servers[0]['data'].get('llm_hass_api') != ['assist']:
    raise RuntimeError('Configure exactly one MCP Server integration exposing only Assist before continuing.')
auth = json.loads((storage / 'auth').read_text())['data']
owners = {u['id'] for u in auth['users'] if u.get('is_owner') and u.get('is_active')}
refresh = next(t for t in auth['refresh_tokens'] if t['user_id'] in owners and t['token_type'] == 'normal' and t.get('client_id'))
if any(t.get('client_name') == 'Hermes Assist' for t in auth['refresh_tokens']):
    raise RuntimeError('Hermes Assist token exists but is missing from the encrypted Secret. Revoke that token in Home Assistant before retrying.')
form = urllib.parse.urlencode({'grant_type':'refresh_token', 'refresh_token':refresh['token'], 'client_id':refresh['client_id']}).encode()
with urllib.request.urlopen('http://127.0.0.1:8123/auth/token', data=form, timeout=15) as r:
    access = json.load(r)['access_token']
async def main():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect('http://127.0.0.1:8123/api/websocket') as ws:
            await ws.receive_json(timeout=15)
            await ws.send_json({'type':'auth','access_token':access})
            if (await ws.receive_json(timeout=15))['type'] != 'auth_ok':
                raise RuntimeError('Home Assistant authentication failed.')
            await ws.send_json({'id':1,'type':'auth/long_lived_access_token','client_name':'Hermes Assist','lifespan':365})
            result = await ws.receive_json(timeout=15)
            if not result.get('success'):
                raise RuntimeError('Home Assistant rejected token creation.')
            print(json.dumps({'token':result['result']}))
asyncio.run(main())
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cluster-age-key', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    target = root / 'cluster/apps/hermes/api-keys.sops.yaml'
    environment = os.environ.copy()
    if args.cluster_age_key:
        result = subprocess.run(['kubectl', '-n', 'flux-system', 'get', 'secret', 'sops-age', '-o', 'json'], check=True, capture_output=True)
        data = json.loads(result.stdout)['data']
        environment['SOPS_AGE_KEY'] = '\n'.join(base64.b64decode(v).decode() for k, v in data.items() if k.endswith(('.agekey', '.txt')))
    result = subprocess.run(['sops', '--decrypt', '--output-type', 'json', str(target)], env=environment, check=True, capture_output=True)
    secret = json.loads(result.stdout)
    if secret['stringData'].get('HOME_ASSISTANT_TOKEN'):
        print('Home Assistant MCP credential is already configured; retained it.')
        return
    result = subprocess.run(['kubectl', '-n', 'house', 'exec', 'deploy/home-assistant', '-c', 'app', '--', 'python3', '-c', PROVISION], check=True, capture_output=True)
    secret['stringData']['HOME_ASSISTANT_TOKEN'] = json.loads(result.stdout)['token']
    result = subprocess.run(['sops', '--encrypt', '--filename-override', str(target), '--input-type', 'json', '--output-type', 'yaml', '/dev/stdin'], input=json.dumps(secret).encode(), env=environment, check=True, capture_output=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.api-keys-', delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(result.stdout)
            handle.close()
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    print('Encrypted the dedicated Hermes Assist token. It expires after 365 days and inherits the owner account permissions.')


if __name__ == '__main__':
    main()
