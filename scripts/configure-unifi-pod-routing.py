#!/usr/bin/env python3
"""Manage the home LAN's narrowly scoped asymmetric Kubernetes TCP exception.

Defaults to a read-only plan. Reads the existing UniFi key from Kubernetes without
printing it. --apply saves the current firewall policies before changing our rule.
"""

import argparse
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import ssl
import subprocess
import urllib.error
import urllib.parse
import urllib.request


NAME = 'Allow asymmetric LAN to Kubernetes pods'
LAN = '10.0.0.0/23'
PODS = '10.42.0.0/16'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        raise RuntimeError('Refusing to redirect a credentialed UniFi API request.')


def desired_policy(internal, external):
    def endpoint(zone, subnet):
        return {'zoneId': zone, 'trafficFilter': {'type': 'IP_ADDRESS', 'ipAddressFilter': {
            'type': 'IP_ADDRESSES', 'matchOpposite': False,
            'items': [{'type': 'SUBNET', 'value': subnet}],
        }}}

    return {
        'enabled': True, 'name': NAME,
        'description': 'Managed by home-ops/scripts/configure-unifi-pod-routing.py. LAN to BGP-routed pods has an asymmetric return path; allow only its INVALID IPv4 TCP state.',
        'action': {'type': 'ALLOW', 'allowReturnTraffic': False},
        'source': endpoint(internal, LAN), 'destination': endpoint(external, PODS),
        'ipProtocolScope': {'ipVersion': 'IPV4', 'protocolFilter': {
            'type': 'NAMED_PROTOCOL', 'protocol': {'name': 'TCP'}, 'matchOpposite': False,
        }},
        'connectionStateFilter': ['INVALID'], 'loggingEnabled': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--apply', action='store_true')
    mode.add_argument('--remove', action='store_true', help='Remove only this exact managed exception.')
    parser.add_argument('--insecure', action='store_true', help='Accept the local controller self-signed TLS certificate.')
    args = parser.parse_args()
    result = subprocess.run(['kubectl', '-n', 'networking', 'get', 'secret', 'external-dns-unifi-secret', '-o', 'json'], check=True, capture_output=True)
    secret = json.loads(result.stdout)['data']
    host = urllib.parse.urlsplit(base64.b64decode(secret['UNIFI_HOST']).decode()).hostname
    if host != '10.0.0.1':
        raise RuntimeError('Expected the home gateway at 10.0.0.1; refusing to change another controller.')
    key = base64.b64decode(secret['UNIFI_API_KEY']).decode()
    context = ssl._create_unverified_context() if args.insecure else ssl.create_default_context()
    opener = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(context=context))
    base = 'https://' + host + '/proxy/network/integration/v1'

    def api(method, path, body=None):
        request = urllib.request.Request(base + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={'X-API-KEY': key, 'Accept': 'application/json', 'Content-Type': 'application/json'}, method=method)
        try:
            with opener.open(request, timeout=20) as response:
                content = response.read()
                return json.loads(content) if content else None
        except urllib.error.HTTPError as error:
            raise RuntimeError(f'UniFi API {method} {path}: HTTP {error.code}') from None

    def collection(path):
        items = []
        while True:
            page = api('GET', path + f'?limit=200&offset={len(items)}')
            items.extend(page['data'])
            if len(items) >= page['totalCount']:
                return items
            if not page['data']:
                raise RuntimeError('UniFi returned an incomplete collection.')

    sites = collection('/sites')
    if len(sites) != 1 or sites[0]['internalReference'] != 'default':
        raise RuntimeError('Expected exactly the Default home site.')
    prefix = '/sites/' + sites[0]['id'] + '/firewall'
    zones = {zone['name'].lower(): zone['id'] for zone in collection(prefix + '/zones')}
    desired = desired_policy(zones['internal'], zones['external'])
    policies = collection(prefix + '/policies')
    owned = [p for p in policies if p['name'] == NAME]
    if len(owned) > 1:
        raise RuntimeError('Duplicate managed policies; inspect them before continuing.')
    existing = owned[0] if owned else None
    same = existing is not None and all(existing.get(k) == v for k, v in desired.items())
    blockers = [p for p in policies if p.get('enabled') and p['source']['zoneId'] == zones['internal']
                and p['destination']['zoneId'] == zones['external'] and p['action']['type'] == 'BLOCK'
                and p.get('connectionStateFilter') == ['INVALID']]
    if len(blockers) != 1:
        raise RuntimeError('Expected one existing Internal-to-External invalid-state block.')
    if existing and existing['index'] >= blockers[0]['index']:
        raise RuntimeError('Managed policy must precede the invalid-state block; inspect policy ordering.')
    print(f'Rule: IPv4 TCP INVALID, {LAN} (Internal) -> {PODS} (External)')
    if not args.apply and not args.remove:
        print('Plan: ' + ('already matches' if same else 'update managed rule' if existing else 'create managed rule'))
        return
    if args.remove and not existing:
        print('Managed rule is already absent.')
        return
    if args.remove and not same:
        raise RuntimeError('The managed rule was changed; refusing to remove a different policy.')
    if args.apply and same:
        print('Managed rule already matches; no changes.')
        return

    directory = Path(__file__).resolve().parents[1] / '.engineering/unifi-firewall'
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    backup = directory / (stamp + '-before.json')
    fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as handle:
        json.dump({'site': sites[0]['id'], 'policies': policies}, handle, indent=2)
    print('Policy snapshot: ' + str(backup))
    if args.remove:
        api('DELETE', prefix + '/policies/' + existing['id'])
        print('Removed managed rule; existing firewall policies retained.')
        return
    created = None
    try:
        if not existing:
            created = api('POST', prefix + '/policies', {**desired, 'enabled': False})
            existing = created
            if created['index'] >= blockers[0]['index']:
                raise RuntimeError('New rule was ordered after the invalid-state block.')
        current = api('PUT', prefix + '/policies/' + existing['id'], desired)
        if not all(current.get(k) == v for k, v in desired.items()):
            raise RuntimeError('UniFi did not retain the exact requested rule.')
    except Exception:
        if created:
            api('DELETE', prefix + '/policies/' + created['id'])
        raise
    print('Applied managed rule: ' + current['id'])
    print('Rollback: python3 scripts/configure-unifi-pod-routing.py --remove' + (' --insecure' if args.insecure else ''))


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))
