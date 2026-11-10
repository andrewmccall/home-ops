#!/usr/bin/env python3
"""Alert decisions for the Alertmanager webhook route (see ../README.md#alert-triage).

With no arguments this is the route's filter: Alertmanager's JSON payload arrives
on stdin. Firing alerts that are new, or whose "later" time has passed, are marked
pending and printed as the agent's payload with Sproozi request fields; all other
alerts are dropped, and an empty output tells Hermes to skip the webhook. Resolved
alerts clear any decision except "ignore".

  sre_alerts.py decide KEY ignore|fix|clear
  sre_alerts.py decide KEY later [--hours N]   (default 24)
  sre_alerts.py list

`decide KEY fix` prints the submit fields for Sproozi's fix workflow.
State is one JSON file, written atomically: $SRE_ALERTS_STATE or
$HERMES_HOME/sre/decisions.json.
"""

import argparse
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

# The label naming the affected object, most specific first.
OBJECT_LABELS = ('deployment', 'statefulset', 'daemonset', 'job_name', 'cronjob', 'persistentvolumeclaim',
                 'container', 'service', 'instance', 'pod')
PENDING_FOR = timedelta(hours=24)  # an unanswered question is asked again after this
REQUEST_LIFETIME = timedelta(minutes=50)  # the task service accepts at most one hour


def state_path():
    if os.environ.get('SRE_ALERTS_STATE'):
        return Path(os.environ['SRE_ALERTS_STATE'])
    return Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes'))) / 'sre' / 'decisions.json'


def now():
    return datetime.now(timezone.utc).replace(microsecond=0)


def stamp(moment):
    return moment.isoformat().replace('+00:00', 'Z')


def parse(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def alert_key(labels):
    obj = next((labels[name] for name in OBJECT_LABELS if labels.get(name)), '-')
    return '/'.join((labels.get('alertname', 'unknown'), labels.get('namespace', '-'), obj))


def request_fields(workflow, key, started):
    digest = hashlib.sha256(f'{workflow}|{key}|{started}'.encode()).hexdigest()[:12]
    return {'workflow': workflow, 'requestId': f'{workflow}-{digest}', 'expiresAt': stamp(now() + REQUEST_LIFETIME)}


class State:
    """The decisions file, locked for the duration of a command."""

    def __init__(self):
        self.path = state_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = open(self.path.with_suffix('.lock'), 'w')
        fcntl.flock(self.lock, fcntl.LOCK_EX)
        self.data = json.loads(self.path.read_text()) if self.path.exists() else {}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.lock.close()  # releases the flock

    def save(self):
        with tempfile.NamedTemporaryFile('w', dir=self.path.parent, delete=False) as handle:
            json.dump(self.data, handle, indent=2, sort_keys=True)
        os.replace(handle.name, self.path)


def should_ask(entry, moment):
    if entry is None:
        return True
    action = entry['action']
    if action == 'later':
        return parse(entry['until']) <= moment
    if action == 'pending':
        return parse(entry['since']) + PENDING_FOR <= moment
    return False  # ignore, fix


def filter_payload(payload):
    with State() as state:
        selected = _select(state, payload, now())
        state.save()
    if selected:
        print(json.dumps({'count': len(selected), 'alerts': selected}, indent=2))


def _select(state, payload, moment):
    selected = []
    for alert in payload.get('alerts', []):
        labels = alert.get('labels', {})
        key = alert_key(labels)
        entry = state.data.get(key)
        if alert.get('status') == 'resolved':
            if entry and entry['action'] != 'ignore':
                del state.data[key]
            continue
        if not should_ask(entry, moment) or any(item['key'] == key for item in selected):
            continue
        state.data[key] = {'action': 'pending', 'since': stamp(moment), 'startsAt': alert.get('startsAt', '')}
        selected.append({
            'key': key,
            'labels': labels,
            'annotations': alert.get('annotations', {}),
            'startsAt': alert.get('startsAt', ''),
            'triage': request_fields('triage', key, alert.get('startsAt', '')),
        })
    return selected


def decide(key, action, hours):
    moment = now()
    with State() as state:
        if action == 'clear':
            state.data.pop(key, None)
            state.save()
            print(f'{key}: cleared')
            return
        started = state.data.get(key, {}).get('startsAt', '')
        record = {'action': action, 'since': stamp(moment), 'startsAt': started}
        if action == 'later':
            record['until'] = stamp(moment + timedelta(hours=hours))
        state.data[key] = record
        state.save()
    if action == 'fix':
        print(json.dumps(request_fields('fix', key, started)))
    elif action == 'later':
        print(f'{key}: ask again after {record["until"]} if still firing')
    else:
        print(f'{key}: ignored until cleared')


def main():
    if len(sys.argv) == 1:
        filter_payload(json.load(sys.stdin))
        return
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    decide_parser = commands.add_parser('decide')
    decide_parser.add_argument('key')
    decide_parser.add_argument('action', choices=('ignore', 'later', 'fix', 'clear'))
    decide_parser.add_argument('--hours', type=float, default=24)
    commands.add_parser('list')
    args = parser.parse_args()
    if args.command == 'decide':
        decide(args.key, args.action, args.hours)
    else:
        with State() as state:
            print(json.dumps(state.data, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
