#!/usr/bin/env python3
"""Verify against the live cluster that monitoring sees the cluster and can tell a human.

Checks Grafana datasources, plugins and platform dashboards, Prometheus scrape
targets, that Loki holds recent logs from every namespace running pods, and that
Alertmanager delivers notifications. Read-only. Requires kubectl and PyYAML.
"""

import base64
import json
from pathlib import Path
import re
import subprocess
import sys
import urllib.parse
import urllib.request

import yaml


ROOT = Path(__file__).resolve().parents[1]
PROMETHEUS = '/api/v1/namespaces/monitoring/services/http:kube-prometheus-stack-prometheus:9090/proxy'
LOKI = '/api/v1/namespaces/monitoring/services/http:loki-gateway:80/proxy'
REQUIRED_JOBS = ('flux-system/helm-controller', 'flux-system/kustomize-controller', 'flux-system/source-controller',
                 'flux-system/notification-controller', 'longhorn-backend', 'monitoring/loki', 'monitoring/vector-agent')
# default only runs the dnsutils debug pod, which sleeps without logging.
SILENT_NAMESPACES = {'default'}


def kubectl(*args):
    return subprocess.run(['kubectl', *args], check=True, capture_output=True, text=True).stdout


def raw(path, **params):
    return json.loads(kubectl('get', '--raw', f'{path}?{urllib.parse.urlencode(params)}' if params else path))


def query(expr):
    return raw(f'{PROMETHEUS}/api/v1/query', query=expr)['data']['result']


class Grafana:
    """The Grafana API through a port-forward, as the admin user."""

    def __enter__(self):
        password = base64.b64decode(kubectl('-n', 'monitoring', 'get', 'secret', 'grafana', '-o', 'jsonpath={.data.admin-password}')).decode()
        self.auth = 'Basic ' + base64.b64encode(f'admin:{password}'.encode()).decode()
        self.forward = subprocess.Popen(['kubectl', '-n', 'monitoring', 'port-forward', 'svc/grafana', ':80'], stdout=subprocess.PIPE, text=True)
        self.base = 'http://127.0.0.1:' + re.search(r'127\.0\.0\.1:(\d+)', self.forward.stdout.readline()).group(1)
        return self

    def __exit__(self, *_):
        self.forward.terminate()

    def get(self, path):
        request = urllib.request.Request(self.base + path, headers={'Authorization': self.auth})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            return json.load(error)


def grafana_errors():
    release = yaml.safe_load((ROOT / 'cluster/apps/monitoring/grafana/helmrelease.yaml').read_text())
    expected = len(release['spec']['values']['dashboards']['platform'])
    with Grafana() as grafana:
        for source in grafana.get('/api/datasources'):
            health = grafana.get(f"/api/datasources/uid/{source['uid']}/health")
            if not source['url'] or health.get('status') != 'OK':
                yield f"Grafana datasource {source['name']} ({source['url'] or 'no URL'}) is unhealthy: {health.get('message')}"
        for error in grafana.get('/api/plugins/errors'):
            yield f"Grafana plugin {error['pluginId']} failed to load: {error['errorCode']}"
        platform = [d for d in grafana.get('/api/search?type=dash-db&limit=5000') if d.get('folderTitle') == 'Platform']
        if len(platform) < expected:
            yield f'Grafana Platform folder has {len(platform)} dashboards; the HelmRelease provisions {expected}'


def prometheus_errors():
    for target in query('up == 0'):
        yield f"Prometheus target {target['metric'].get('job')} {target['metric'].get('instance')} is down"
    jobs = {r['metric']['job'] for r in query('sum by (job) (up)')}
    for job in REQUIRED_JOBS:
        if job not in jobs:
            yield f'Prometheus is not scraping {job}'
    if not query('gotk_resource_info{customresource_kind="HelmRelease"}'):
        yield 'Prometheus has no Flux HelmRelease state metrics; FluxReconciliationFailure cannot fire'


def loki_errors():
    pods = json.loads(kubectl('get', 'pods', '-A', '--field-selector=status.phase=Running', '-o', 'json'))['items']
    running = {pod['metadata']['namespace'] for pod in pods} - SILENT_NAMESPACES
    logged = set(raw(f'{LOKI}/loki/api/v1/label/namespace/values', since='1h')['data'])
    for namespace in sorted(running - logged):
        yield f'Loki has no logs from namespace {namespace} in the last hour'


def alertmanager_errors():
    for result in query('sum by (integration) (increase(alertmanager_notifications_failed_total[1h])) > 0'):
        yield f"Alertmanager failed {float(result['value'][1]):.0f} {result['metric']['integration']} notifications in the last hour"


def main():
    errors = []
    for name, check in (('Grafana', grafana_errors), ('Prometheus', prometheus_errors), ('Loki', loki_errors), ('Alertmanager', alertmanager_errors)):
        failures = list(check())
        errors += failures
        if not failures:
            print(f'PASS: {name}')
    for error in errors:
        print(f'FAIL: {error}', file=sys.stderr)
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
