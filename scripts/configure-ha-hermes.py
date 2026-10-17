#!/usr/bin/env python3
"""Connect Ada's existing Home Assistant conversation integration to Hermes.

Uses Home Assistant's configuration flows and an existing owner's refresh token.
Credentials stay in memory. Verification runs one paid request through Ada and Piper.
"""

import asyncio
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.parse
import urllib.request


ENDPOINT = 'http://hermes-api.hermes.svc:8642/v1'


def configure(payload):
    import aiohttp

    if os.environ.get('OPENAI_BASE_URL') != ENDPOINT:
        raise RuntimeError('Wait for the Home Assistant endpoint rollout before configuring its credential.')
    storage = Path('/config/.storage')
    auth = json.loads((storage / 'auth').read_text())['data']
    owners = {user['id'] for user in auth['users'] if user.get('is_owner') and user.get('is_active')}
    refresh = next(token for token in auth['refresh_tokens'] if token['user_id'] in owners and token['token_type'] == 'normal' and token.get('client_id'))
    form = urllib.parse.urlencode({'grant_type': 'refresh_token', 'refresh_token': refresh['token'], 'client_id': refresh['client_id']}).encode()
    with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8123/auth/token', data=form), timeout=15) as response:
        access = json.load(response)['access_token']

    def request(path, body):
        headers = {'Authorization': 'Bearer ' + access, 'Content-Type': 'application/json'}
        with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8123' + path, data=json.dumps(body).encode(), headers=headers), timeout=60) as response:
            return json.load(response)

    def finish(result):
        if result.get('type') != 'abort' or result.get('reason') not in ('reconfigure_successful', 'reauth_successful'):
            raise RuntimeError(f'Configuration did not finish: {result.get("type")}, {result.get("step_id")}, {result.get("errors") or result.get("reason")}')

    entries = json.loads((storage / 'core.config_entries').read_text())['data']['entries']
    entries = [entry for entry in entries if entry['domain'] == 'openai_conversation']
    assert len(entries) == 1, 'Expected exactly one existing OpenAI integration.'
    entry = entries[0]
    subentries = [subentry for subentry in entry['subentries'] if subentry['subentry_type'] == 'conversation']
    assert len(subentries) == 1, 'Expected exactly one conversation subentry.'
    subentry = subentries[0]
    options = subentry['data']

    if entry['data']['api_key'] != payload['gateway_key']:
        flow = request('/api/config/config_entries/flow', {'handler': 'openai_conversation', 'entry_id': entry['entry_id']})
        finish(request('/api/config/config_entries/flow/' + flow['flow_id'], {'api_key': payload['gateway_key']}))
        print('Updated the existing Home Assistant integration credential.')

    if options.get('chat_model') != payload['model']:
        for _ in range(30):
            flow = request('/api/config/config_entries/subentries/flow', {'handler': [entry['entry_id'], 'conversation'], 'subentry_id': subentry['subentry_id']})
            if flow.get('reason') != 'entry_not_loaded':
                break
            time.sleep(1)
        assert flow.get('type') == 'form', 'Conversation integration did not finish loading.'
        path = '/api/config/config_entries/subentries/flow/' + flow['flow_id']
        initial = {key: options[key] for key in ('prompt', 'llm_hass_api') if key in options}
        initial['recommended'] = False
        flow = request(path, initial)
        assert flow.get('step_id') == 'additional', 'Unexpected conversation configuration step.'
        additional = {key: options[key] for key in ('max_tokens', 'top_p', 'temperature', 'store_responses') if key in options}
        additional['chat_model'] = payload['model']
        flow = request(path, additional)
        assert flow.get('step_id') == 'model', 'Model options were rejected.'
        allowed = {field['name'] for field in flow['data_schema']}
        finish(request(path, {key: value for key, value in options.items() if key in allowed}))
        print('Updated the conversation model; retained the existing prompt and exposed-entity API selection.')

    pipeline_data = json.loads((storage / 'assist_pipeline.pipelines').read_text())['data']
    pipeline = next(p for p in pipeline_data['items'] if p['id'] == pipeline_data['preferred_item'])
    assert pipeline['conversation_engine'] == 'conversation.openai_conversation'

    async def verify():
        speech = None
        audio = None
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect('http://127.0.0.1:8123/api/websocket', timeout=15) as ws:
                await ws.receive_json(timeout=15)
                await ws.send_json({'type': 'auth', 'access_token': access})
                assert (await ws.receive_json(timeout=15))['type'] == 'auth_ok'
                await ws.send_json({'id': 1, 'type': 'assist_pipeline/run', 'pipeline': pipeline['id'], 'start_stage': 'intent', 'end_stage': 'tts', 'timeout': 120, 'input': {'text': 'Reply with exactly: Hermes voice ready. Do not use any tools.'}})
                while True:
                    message = await ws.receive_json(timeout=150)
                    if message['type'] == 'result' and not message.get('success'):
                        raise RuntimeError('Ada pipeline request rejected: ' + str(message.get('error', {}).get('code')))
                    event = message.get('event', {})
                    if event.get('type') == 'error':
                        raise RuntimeError('Ada pipeline failed: ' + str(event.get('data')))
                    if event.get('type') == 'intent-end':
                        speech = event['data']['intent_output']['response']['speech']['plain']['speech']
                    if event.get('type') == 'tts-end':
                        audio = event['data']['tts_output']
                    if event.get('type') == 'run-end':
                        break
        assert speech and speech.strip().lower().rstrip('.') == 'hermes voice ready', 'Ada did not return the expected Hermes readiness reply.'
        assert audio and audio.get('url'), 'Piper did not generate speech audio.'
        print('PASS: Ada pipeline routed a text request through Hermes and generated Piper speech audio.')

    asyncio.run(verify())


def main():
    if '--in-container' in sys.argv:
        configure(json.load(sys.stdin))
        return
    import yaml

    root = Path(__file__).resolve().parents[1]
    model = yaml.safe_load((root / 'cluster/apps/hermes/config.yaml').read_text())['model']['default']
    result = subprocess.run(['kubectl', '-n', 'hermes', 'get', 'secret', 'hermes-agent-api-keys', '-o', 'json'], check=True, capture_output=True)
    key = base64.b64decode(json.loads(result.stdout)['data']['API_SERVER_KEY']).decode()
    subprocess.run(
        ['kubectl', '-n', 'house', 'exec', '-i', 'deploy/home-assistant', '-c', 'app', '--', 'python3', '-c', Path(__file__).read_text(), '--in-container'],
        input=json.dumps({'gateway_key': key, 'model': model}).encode(), check=True,
    )


if __name__ == '__main__':
    main()
