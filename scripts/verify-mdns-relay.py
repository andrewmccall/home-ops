#!/usr/bin/env python3
"""Read-only check of scoped Music Assistant discovery and reachable LAN services."""
import argparse
import json
import subprocess

# Run in the existing Music Assistant image; no host Python packages required.
BROWSE = r'''
import asyncio,json,socket
from zeroconf import ServiceStateChange
from zeroconf.asyncio import AsyncZeroconf,AsyncServiceBrowser,AsyncServiceInfo
async def main():
    z=AsyncZeroconf(); names=set()
    def changed(zeroconf,service_type,name,state_change):
        if state_change is not ServiceStateChange.Removed: names.add((service_type,name))
    browser=AsyncServiceBrowser(z.zeroconf,['_spotify-connect._tcp.local.','_sendspin._tcp.local.','_ssh._tcp.local.'],handlers=[changed])
    await asyncio.sleep(10)
    results=[]
    try:
        for kind,name in sorted(names):
            info=AsyncServiceInfo(kind,name)
            if not await info.async_request(z.zeroconf,2000): continue
            addresses=info.parsed_scoped_addresses()
            reachable=[]
            for address in addresses:
                try:
                    connection=socket.create_connection((address,info.port),2)
                    connection.close(); reachable.append(address)
                except OSError: pass
            results.append({'type':kind,'name':name,'addresses':addresses,'port':info.port,'reachable':reachable})
        print(json.dumps(results))
    finally:
        await browser.async_cancel(); await z.async_close()
asyncio.run(main())
'''


def kubectl(*args, source=None):
    return subprocess.run(['kubectl', *args], input=source, text=True, capture_output=True, check=True).stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pod', help='An opted-in test pod; defaults to Music Assistant')
    args = parser.parse_args()
    pods = json.loads(kubectl('-n', 'house', 'get', 'pods', '-l', 'home-ops.andrewmccall.com/mdns-relay=music-assistant', '-o', 'json'))['items']
    pods = [p for p in pods if not p['metadata'].get('deletionTimestamp') and p['status'].get('phase') == 'Running']
    if len(pods) != 1:
        raise RuntimeError(f'Expected exactly one running opted-in pod, found {len(pods)}')
    pod = pods[0]
    name = pod['metadata']['name']
    if args.pod and name != args.pod:
        raise RuntimeError('The selected test pod is not the relay target')
    if pod['spec'].get('hostNetwork'):
        raise RuntimeError('Target is still using host networking')
    status = json.loads(kubectl('-n', 'networking', 'exec', 'ds/avahi-relay', '-c', 'controller', '--', 'cat', '/run/relay/status.json'))
    if not str(status.get('interface') or '').startswith('cali') or status.get('error'):
        raise RuntimeError(f'Relay has no healthy target: {status}')
    discovered = json.loads(kubectl('-n', 'house', 'exec', '-i', name, '--', '/app/venv/bin/python3', '-', source=BROWSE))
    print(json.dumps({'pod': name, 'address': pod['status']['podIP'], 'interface': status['interface'], 'services': discovered}, indent=2))
    if any(d['type'] == '_ssh._tcp.local.' for d in discovered):
        raise RuntimeError('Unexpected SSH discovery in scoped pod')
    for kind in ('_spotify-connect._tcp.local.', '_sendspin._tcp.local.'):
        if not any(d['type'] == kind and d['reachable'] for d in discovered):
            raise RuntimeError(f'No reachable LAN service discovered for {kind}')
    print('PASS: pod networking, scoped Spotify/Sendspin discovery and TCP connectivity. Audible playback still requires a speaker check.')


if __name__ == '__main__':
    main()
