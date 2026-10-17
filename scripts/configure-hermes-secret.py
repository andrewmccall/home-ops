#!/usr/bin/env python3
"""Encrypt Hermes credentials without writing plaintext secrets to disk."""

import argparse
import base64
import getpass
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--key-file', type=Path, help='Read the new OpenRouter key from this file; otherwise prompt securely.')
    parser.add_argument('--cluster-age-key', action='store_true', help='Use the age identity from flux-system/sops-age in memory.')
    args = parser.parse_args()
    target = Path(__file__).resolve().parents[1] / 'cluster/apps/hermes/api-keys.sops.yaml'
    key = args.key_file.read_text().strip() if args.key_file else getpass.getpass('New Hermes OpenRouter API key: ').strip()
    if not key.startswith('sk-or-') or any(c.isspace() for c in key):
        parser.error('Expected a single OpenRouter API key starting with sk-or-.')

    environment = os.environ.copy()
    if args.cluster_age_key:
        identity = subprocess.run(
            ['kubectl', '-n', 'flux-system', 'get', 'secret', 'sops-age', '-o', 'json'],
            check=True, capture_output=True,
        )
        data = json.loads(identity.stdout)['data']
        identities = [base64.b64decode(value).decode() for name, value in data.items() if name.endswith(('.agekey', '.txt'))]
        if not identities:
            parser.error('flux-system/sops-age has no .agekey or .txt identity entry.')
        environment['SOPS_AGE_KEY'] = '\n'.join(identities)

    api_key = secrets.token_hex(32)
    credentials = {}
    if target.exists():
        previous = subprocess.run(['sops', '--decrypt', '--output-type', 'json', str(target)], env=environment, check=True, capture_output=True)
        credentials = json.loads(previous.stdout)['stringData']
        api_key = credentials['API_SERVER_KEY']
    secret = {
        'apiVersion': 'v1', 'kind': 'Secret',
        'metadata': {'name': 'hermes-agent-api-keys', 'namespace': 'hermes'},
        'type': 'Opaque',
        'stringData': {**credentials, 'OPENROUTER_API_KEY': key, 'API_SERVER_KEY': api_key},
    }
    encrypted = subprocess.run(
        ['sops', '--encrypt', '--filename-override', str(target), '--input-type', 'json', '--output-type', 'yaml', '/dev/stdin'],
        input=json.dumps(secret).encode(), env=environment, check=True, capture_output=True,
    ).stdout
    with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.api-keys-', delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(encrypted)
            handle.close()
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    print('Encrypted Hermes credentials saved. The gateway API key was preserved if already configured.')


if __name__ == '__main__':
    main()
