"""Keep Avahi attached only to the opted-in local pod's Calico link."""

import ipaddress
import json
import os
from pathlib import Path
import re
import signal
import ssl
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request


SHARED = Path('/run/relay')
STATE = Path('/var/lib/relay/owned.json')
CONFIG = SHARED / 'avahi-daemon.conf'
GATEWAY = '169.254.1.1/32'
STOP = threading.Event()


def write(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(value)
    temporary.chmod(0o644)
    temporary.replace(path)


def ip(*args):
    return subprocess.run(['ip', *args], check=True, capture_output=True, text=True, timeout=5).stdout


def addresses(interface):
    return re.findall(r'\binet\s+(\S+)', ip('-4', '-o', 'address', 'show', 'dev', interface))


def select_target(pods, node):
    candidates = [p for p in pods if p['spec'].get('nodeName') == node
                  and not p['spec'].get('hostNetwork') and not p['metadata'].get('deletionTimestamp')
                  and p['status'].get('phase') == 'Running' and p['status'].get('podIP')]
    if len(candidates) > 1:
        raise RuntimeError('More than one opted-in pod on this node; refusing to broaden reflection.')
    return candidates[0] if candidates else None


def interface_index(interface):
    path = Path('/sys/class/net', interface, 'ifindex')
    return int(path.read_text()) if path.exists() else None


def cleanup():
    CONFIG.unlink(missing_ok=True)
    if not STATE.exists():
        return
    state = json.loads(STATE.read_text())
    interface = state['interface']
    if state['owned'] and interface_index(interface) == state['ifindex']:
        address = str(ipaddress.IPv4Address(state['address']))
        if GATEWAY in addresses(interface):
            # Removing the last IPv4 address flushes link routes. Journal the
            # existing Calico route before removal so a crash can recover it.
            routes = ip('-4', 'route', 'show', 'dev', interface)
            state['restore_route'] = any(re.fullmatch(re.escape(address) + r'(?:/32)?\s+(?:dev\s+' + re.escape(interface) + r'\s+)?scope link\s*', line)
                                         for line in routes.splitlines())
            write(STATE, json.dumps(state))
            ip('address', 'del', GATEWAY, 'dev', interface)
        if state.get('restore_route') and interface_index(interface) == state['ifindex']:
            ip('route', 'replace', address + '/32', 'dev', interface, 'scope', 'link')
    STATE.unlink()


def configure(pod, lan, service_types):
    address = str(ipaddress.IPv4Address(pod['status']['podIP']))
    route = ip('route', 'get', address)
    match = re.search(r'\bdev\s+(cali[a-zA-Z0-9]+)\b', route)
    if not match:
        raise RuntimeError('Target pod does not have a local Calico interface.')
    interface = match[1]
    previous = json.loads(STATE.read_text()) if STATE.exists() else None
    index = interface_index(interface)
    if previous and (previous['interface'] != interface or previous['ifindex'] != index):
        cleanup()
        previous = None
    current = addresses(interface)
    if GATEWAY in current and not (previous and previous['owned']):
        raise RuntimeError('Target interface has an unowned relay address; refusing to adopt it.')
    owned = not current or bool(previous and previous['owned'])
    # Persist ownership intent before mutation, including across container restarts.
    write(STATE, json.dumps({'interface': interface, 'ifindex': index, 'address': address, 'owned': owned}))
    if owned and GATEWAY not in current:
        ip('address', 'add', GATEWAY, 'dev', interface)
    text = f'''[server]
use-ipv4=yes
use-ipv6=no
enable-dbus=no
allow-interfaces={lan},{interface}
check-response-ttl=yes
[publish]
disable-publishing=yes
publish-addresses=no
publish-workstation=no
[reflector]
enable-reflector=yes
reflect-ipv=no
reflect-filters={','.join(service_types)}
'''
    if not CONFIG.exists() or CONFIG.read_text() != text:
        write(CONFIG, text)
        print(f'Relay target {pod["metadata"]["name"]} {address}: {lan} <-> {interface}', flush=True)
    return interface


def main():
    if '--health' in sys.argv:
        status = json.loads((SHARED / 'status.json').read_text())
        return 0 if time.time() - status['last_success'] < 25 else 1
    lan = os.environ['LAN_INTERFACE']
    if not re.fullmatch(r'[a-zA-Z0-9_.-]{1,15}', lan) or not Path('/sys/class/net', lan).exists():
        raise RuntimeError('LAN_INTERFACE must identify an existing interface.')
    types = os.environ['SERVICE_TYPES'].split(',')
    if not all(re.fullmatch(r'_[a-zA-Z0-9-]+\._(?:tcp|udp)\.local', t) for t in types):
        raise RuntimeError('SERVICE_TYPES must contain explicit DNS-SD service types.')
    node = os.environ['NODE_NAME']
    namespace = os.environ['TARGET_NAMESPACE']
    query = urllib.parse.urlencode({'labelSelector': os.environ['TARGET_SELECTOR'], 'fieldSelector': 'spec.nodeName=' + node})
    url = f'https://{os.environ["KUBERNETES_SERVICE_HOST"]}:{os.environ["KUBERNETES_SERVICE_PORT_HTTPS"]}/api/v1/namespaces/{namespace}/pods?{query}'
    context = ssl.create_default_context(cafile='/var/run/kubernetes/ca.crt')
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: STOP.set())
    last_success = 0
    try:
        while not STOP.is_set():
            try:
                token = Path('/var/run/kubernetes/token').read_text().strip()
                request = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + token})
                with urllib.request.urlopen(request, context=context, timeout=8) as response:
                    pods = json.load(response)['items']
                target = select_target(pods, node)
                if target:
                    interface = configure(target, lan, types)
                else:
                    cleanup()
                    interface = None
                last_success = time.time()
                write(SHARED / 'status.json', json.dumps({'last_success': last_success, 'interface': interface}))
            except Exception as error:
                print(f'Relay disabled: {type(error).__name__}: {error}', flush=True)
                cleanup()
                write(SHARED / 'status.json', json.dumps({'last_success': last_success, 'error': str(error)}))
            STOP.wait(3)
    finally:
        cleanup()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
