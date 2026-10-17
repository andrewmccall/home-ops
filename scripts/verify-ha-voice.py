#!/usr/bin/env python3
"""Exercise Ada from synthetic speech through STT, Hermes and Piper.

Runs one paid conversation request; --mcp adds a second, read-only state query.
Does not test the physical satellite.
"""

import subprocess
import sys


PROBE = r'''
import asyncio, json, urllib.parse, urllib.request
from pathlib import Path
import aiohttp
from wyoming.audio import AudioStart, AudioChunk, AudioStop
from wyoming.client import AsyncTcpClient
from wyoming.tts import Synthesize, SynthesizeVoice

async def main():
    pcm = bytearray()
    rate = None
    async with AsyncTcpClient('home-assistant-voice', 10200) as client:
        await client.write_event(Synthesize(text='What is your name?', voice=SynthesizeVoice(name='en_GB-cori-high')).event())
        while (event := await asyncio.wait_for(client.read_event(), 120)) is not None:
            if AudioStart.is_type(event.type):
                start = AudioStart.from_event(event)
                if start.width != 2 or start.channels != 1:
                    raise RuntimeError('Expected 16-bit mono Piper audio.')
                rate = start.rate
            elif AudioChunk.is_type(event.type):
                pcm.extend(AudioChunk.from_event(event).audio)
            elif AudioStop.is_type(event.type):
                break
    if not rate or not pcm:
        raise RuntimeError('Piper did not synthesise the test question.')
    storage = Path('/config/.storage')
    auth = json.loads((storage / 'auth').read_text())['data']
    owners = {u['id'] for u in auth['users'] if u.get('is_owner') and u.get('is_active')}
    t = next(t for t in auth['refresh_tokens'] if t['user_id'] in owners and t['token_type']=='normal' and t.get('client_id'))
    form = urllib.parse.urlencode({'grant_type':'refresh_token','refresh_token':t['token'],'client_id':t['client_id']}).encode()
    with urllib.request.urlopen('http://127.0.0.1:8123/auth/token', data=form, timeout=15) as r:
        access = json.load(r)['access_token']
    pipeline = json.loads((storage / 'assist_pipeline.pipelines').read_text())['data']['preferred_item']
    transcript = speech = audio = None
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect('http://127.0.0.1:8123/api/websocket') as ws:
            await ws.receive_json(timeout=15)
            await ws.send_json({'type':'auth','access_token':access})
            if (await ws.receive_json(timeout=15))['type'] != 'auth_ok':
                raise RuntimeError('Home Assistant authentication failed.')
            await ws.send_json({'id':1,'type':'assist_pipeline/run','pipeline':pipeline,'start_stage':'stt','end_stage':'tts','timeout':120,'input':{'sample_rate':rate}})
            while True:
                message = await ws.receive_json(timeout=150)
                if message['type']=='result' and not message.get('success'):
                    raise RuntimeError(str(message.get('error')))
                event = message.get('event', {})
                kind, data = event.get('type'), event.get('data', {})
                if kind=='run-start':
                    prefix = bytes([data['runner_data']['stt_binary_handler_id']])
                    for offset in range(0,len(pcm),2048):
                        await ws.send_bytes(prefix + pcm[offset:offset+2048])
                    await ws.send_bytes(prefix)
                if kind=='error':
                    raise RuntimeError(str(data))
                if kind=='stt-end':
                    transcript=data['stt_output']['text']
                if kind=='intent-end':
                    speech=data['intent_output']['response']['speech']['plain']['speech']
                if kind=='tts-end':
                    audio=data['tts_output']
                if kind in ('stt-end','intent-end','tts-end','run-end'):
                    print(json.dumps({'stage':kind,'timestamp':event.get('timestamp')},ensure_ascii=False),flush=True)
                if kind=='run-end':
                    break
        if not transcript or 'what is your name' not in transcript.lower().replace("what's", 'what is').strip('?. '):
            raise RuntimeError('Incorrect transcription: '+str(transcript))
        if not speech or not audio or not audio.get('url'):
            raise RuntimeError('Missing conversation reply or speech audio.')
        url=urllib.parse.urljoin('http://127.0.0.1:8123',audio['url'])
        async with session.get(url) as response:
            response.raise_for_status()
            sound=await response.read()
            if len(sound)<1000:
                raise RuntimeError('Generated audio was empty or too short.')
        print(json.dumps({'transcript':transcript,'reply':speech,'audio_bytes':len(sound),'result':'PASS'},ensure_ascii=False))
asyncio.run(main())
'''

MCP_PROBE = r'''
import json, os, sqlite3, urllib.request, uuid
session = 'voice-mcp-check-' + uuid.uuid4().hex
body = {'model':'google/gemini-3-flash-preview','messages':[
    {'role':'system','content':'You are a concise home voice assistant. Use the Home Assistant MCP tools when live state is requested.'},
    {'role':'user','content':'Read the current state of the office lights from Home Assistant. Do not change any devices. Answer in one short sentence.'}]}
request = urllib.request.Request('http://127.0.0.1:8642/v1/chat/completions',data=json.dumps(body).encode(),headers={
    'Authorization':'Bearer '+os.environ['API_SERVER_KEY'],'Content-Type':'application/json','X-Hermes-Session-Id':session})
with urllib.request.urlopen(request,timeout=120) as response:
    result = json.load(response)
connection = sqlite3.connect('file:/opt/data/state.db?mode=ro',uri=True)
rows = connection.execute('select tool_name,content from messages where session_id=? order by id',(session,)).fetchall()
context = next((content for name,content in rows if name=='mcp__home_assistant__homeassistant__GetLiveContext'),None)
if not context or 'Live Context:' not in context:
    raise RuntimeError('No successful Home Assistant live-context tool result was recorded.')
print(json.dumps({'result':'PASS','tool':'Home Assistant GetLiveContext','reply':result['choices'][0]['message']['content']}))
'''


def main():
    subprocess.run(['kubectl', '-n', 'house', 'exec', 'deploy/home-assistant', '-c', 'app', '--', 'python3', '-u', '-c', PROBE], check=True)
    if '--mcp' in sys.argv:
        subprocess.run(['kubectl', '-n', 'hermes', 'exec', 'hermes', '-c', 'hermes', '--', 'python3', '-u', '-c', MCP_PROBE], check=True)


if __name__ == '__main__':
    main()
