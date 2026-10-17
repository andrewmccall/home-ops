#!/usr/bin/env python3
"""Render every Flux HelmRelease with helm and fail on errors Flux would hit when upgrading.

helm template validates values against each chart's schema. With --base REF, the
renders are also compared with that git revision, and changes to fields Kubernetes
cannot update in place fail. Requires helm, kubectl, git and PyYAML.

Limitations: SOPS-encrypted substitution variables render as placeholders, and
postRenderers are not applied.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import yaml


ROOT = Path(__file__).resolve().parents[1]
ENTRY_POINTS = ('base', 'core', 'apps')
KUBE_VERSION = '1.35.0'
VARIABLE = re.compile(r'\$\{([A-Za-z_][A-Za-z0-9_]*)(?::?[=-]([^}]*))?\}')
WORKLOAD_SELECTOR_KINDS = ('Deployment', 'DaemonSet', 'ReplicaSet')
STATEFULSET_MUTABLE = {'replicas', 'template', 'updateStrategy', 'persistentVolumeClaimRetentionPolicy', 'minReadySeconds', 'ordinals', 'revisionHistoryLimit'}
PVC_IMMUTABLE = ('accessModes', 'storageClassName', 'volumeName', 'volumeMode')
# PyYAML resolves a bare "=" to the YAML 1.1 value tag; Kubernetes treats it as a string.
yaml.SafeLoader.add_constructor('tag:yaml.org,2002:value', yaml.SafeLoader.construct_yaml_str)


def render_tree(root):
    """Return the documents of each Flux entry point under root/cluster."""
    documents = []
    for name in ENTRY_POINTS:
        result = subprocess.run(['kubectl', 'kustomize', str(root / 'cluster' / name)], check=True, capture_output=True, text=True)
        documents += [doc for doc in yaml.safe_load_all(result.stdout) if doc]
    return documents


def substitutions(documents):
    """Mirror postBuild.substituteFrom: cluster-config values, placeholders for encrypted secrets."""
    values = {}
    for doc in documents:
        if doc['kind'] == 'Secret' and doc['metadata']['name'] == 'cluster-secrets':
            values |= {key: f'placeholder-{key.lower()}' for key in {**doc.get('data', {}), **doc.get('stringData', {})}}
    for doc in documents:
        if doc['kind'] == 'ConfigMap' and doc['metadata']['name'] == 'cluster-config':
            values |= doc['data']
    return values


def substitute(document, values):
    text = VARIABLE.sub(lambda m: values.get(m.group(1), m.group(2) if m.group(2) is not None else ''), json.dumps(document))
    return json.loads(text)


def api_versions(documents):
    versions = set()
    for doc in documents:
        if doc['kind'] == 'CustomResourceDefinition':
            spec = doc['spec']
            versions |= {f"{spec['group']}/{v['name']}" for v in spec['versions'] if v.get('served', True)}
            versions |= {f"{spec['group']}/{v['name']}/{spec['names']['kind']}" for v in spec['versions'] if v.get('served', True)}
    return sorted(versions)


def render_release(release, repositories, apis, workdir):
    """Return (rendered documents, error) for one HelmRelease."""
    meta, spec = release['metadata'], release['spec']
    chart = spec['chart']['spec']
    source = chart['sourceRef']
    url = repositories.get((source.get('namespace', meta['namespace']), source['name']))
    if url is None:
        return None, f"HelmRepository {source.get('namespace', meta['namespace'])}/{source['name']} is not defined in git"
    values = Path(workdir) / f"{meta['namespace']}-{meta['name']}.yaml"
    values.write_text(yaml.safe_dump(spec.get('values') or {}))
    if url.startswith('oci://'):
        reference = ['helm', 'template', meta['name'], f"{url.rstrip('/')}/{chart['chart']}"]
    else:
        reference = ['helm', 'template', meta['name'], chart['chart'], '--repo', url]
    command = reference + ['--version', str(chart.get('version', '')), '--namespace', meta['namespace'],
                           '--kube-version', KUBE_VERSION, '--include-crds', '-f', str(values)]
    command += [arg for api in apis for arg in ('--api-versions', api)]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        stderr = [line for line in result.stderr.splitlines() if not line.startswith('WARNING: Kubernetes configuration file')]
        return None, '\n    '.join(stderr)
    return [doc for doc in yaml.safe_load_all(result.stdout) if doc], None


def release_policy_errors(documents):
    """Every Flux Kustomization that applies HelmReleases must patch in rollback remediation."""
    for name in ('apps', 'core'):
        kustomization = next(d for d in documents if d['kind'] == 'Kustomization' and d['metadata']['name'] == name
                             and d['apiVersion'].startswith('kustomize.toolkit.fluxcd.io/'))
        policies = [yaml.safe_load(p['patch'])['spec'] for p in kustomization['spec'].get('patches', [])
                    if p.get('target', {}).get('kind') == 'HelmRelease']
        if not any(p.get('upgrade', {}).get('remediation', {}).get('strategy') == 'rollback'
                   and p.get('install', {}).get('remediation', {}).get('retries') for p in policies):
            yield f'Kustomization flux-system/{name}: missing the HelmRelease install retry and upgrade rollback patch'


def render_releases(root):
    """Return {namespace/name: documents} and a list of errors for every HelmRelease under root."""
    documents = render_tree(root)
    values = substitutions(documents)
    repositories = {(d['metadata']['namespace'], d['metadata']['name']): d['spec']['url']
                    for d in documents if d['kind'] == 'HelmRepository'}
    releases = [substitute(d, values) for d in documents if d['kind'] == 'HelmRelease']
    apis = api_versions(render_crds(root))
    rendered, errors = {}, []
    with tempfile.TemporaryDirectory() as workdir, ThreadPoolExecutor(8) as pool:
        results = pool.map(lambda r: render_release(r, repositories, apis, workdir), releases)
        for release, (docs, error) in zip(releases, results):
            key = f"{release['metadata']['namespace']}/{release['metadata']['name']}"
            if error:
                errors.append(f'{key}: {error}')
            else:
                rendered[key] = docs
    return rendered, errors


def render_crds(root):
    result = subprocess.run(['kubectl', 'kustomize', str(root / 'cluster' / 'crds')], check=True, capture_output=True, text=True)
    crds = [doc for doc in yaml.safe_load_all(result.stdout) if doc]
    # Flux also installs CRDs from remote sources; the monitoring group is the one charts probe for.
    for group, kind in (('monitoring.coreos.com', 'ServiceMonitor'), ('monitoring.coreos.com', 'PodMonitor'), ('monitoring.coreos.com', 'PrometheusRule')):
        crds.append({'kind': 'CustomResourceDefinition', 'spec': {'group': group, 'names': {'kind': kind}, 'versions': [{'name': 'v1'}]}})
    return crds


def immutable_fields(doc):
    """Return the fields of doc that Kubernetes rejects changes to, or None."""
    spec = doc.get('spec') or {}
    if doc['kind'] in WORKLOAD_SELECTOR_KINDS:
        return {'selector': spec.get('selector')}
    if doc['kind'] == 'StatefulSet':
        return {key: value for key, value in spec.items() if key not in STATEFULSET_MUTABLE}
    if doc['kind'] == 'PersistentVolumeClaim':
        return {key: spec.get(key) for key in PVC_IMMUTABLE}
    return None


def objects(documents, namespace):
    return {(d['kind'], d['metadata'].get('namespace', namespace), d['metadata']['name']): d for d in documents
            if 'helm.sh/hook' not in (d['metadata'].get('annotations') or {})}


def immutable_changes(base, head):
    """Yield a message for each object whose immutable fields differ between base and head renders."""
    for release in sorted(base.keys() & head.keys()):
        namespace = release.split('/')[0]
        before, after = objects(base[release], namespace), objects(head[release], namespace)
        for key in sorted(before.keys() & after.keys()):
            old, new = immutable_fields(before[key]), immutable_fields(after[key])
            if old is not None and old != new:
                fields = sorted(k for k in old.keys() | new.keys() if old.get(k) != new.get(k))
                yield (f"{release}: {key[0]}/{key[2]} changes immutable field(s) {', '.join(fields)}; "
                       f"Flux cannot upgrade it in place. Delete {key[0]}/{key[2]} during rollout or keep the old values.")


def base_tree(ref, directory):
    archive = subprocess.run(['git', '-C', str(ROOT), 'archive', ref, 'cluster'], check=True, capture_output=True)
    subprocess.run(['tar', '-x', '-C', directory], input=archive.stdout, check=True)
    return Path(directory)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--base', help='git revision to compare immutable fields against, e.g. origin/main')
    args = parser.parse_args()

    head, errors = render_releases(ROOT)
    policy = list(release_policy_errors(render_tree(ROOT)))
    errors += policy
    if not policy:
        print('PASS: apps and core retry failed installs and roll back failed upgrades')
    for release in sorted(head):
        print(f'PASS: {release} renders and its values match the chart schema')
    if args.base:
        with tempfile.TemporaryDirectory() as directory:
            base, _ = render_releases(base_tree(args.base, directory))
        changes = list(immutable_changes(base, head))
        errors += changes
        if not changes:
            print(f'PASS: no immutable field changes relative to {args.base}')
    for error in errors:
        print(f'FAIL: {error}', file=sys.stderr)
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
