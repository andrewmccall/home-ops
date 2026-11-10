#!/usr/bin/env python3
"""Set keys in a SOPS-encrypted Secret without writing plaintext to disk or the terminal.

Each KEY is prompted for without echo. KEY=@/path reads the value from a file
(for example a GitHub App private key). Existing keys in the Secret are kept.
The file is created if missing, so the Secret's name and namespace are required.

  python3 scripts/sops-set-secret.py --cluster-age-key \\
      cluster/apps/hermes/api-keys.sops.yaml hermes hermes-agent-api-keys ANTHROPIC_API_KEY
"""

import argparse
import base64
import getpass
import json
import os
from pathlib import Path
import subprocess
import tempfile


def age_identity():
    result = subprocess.run(['kubectl', '-n', 'flux-system', 'get', 'secret', 'sops-age', '-o', 'json'],
                            check=True, capture_output=True)
    data = json.loads(result.stdout)['data']
    identities = [base64.b64decode(v).decode() for k, v in data.items() if k.endswith(('.agekey', '.txt'))]
    if not identities:
        raise SystemExit('flux-system/sops-age has no .agekey or .txt identity entry.')
    return '\n'.join(identities)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('file', type=Path, help='Secret manifest ending in .sops.yaml under cluster/')
    parser.add_argument('namespace')
    parser.add_argument('name')
    parser.add_argument('keys', nargs='+', metavar='KEY[=@FILE]')
    parser.add_argument('--cluster-age-key', action='store_true',
                        help='Decrypt with the age identity from flux-system/sops-age, held in memory.')
    args = parser.parse_args()
    if not args.file.name.endswith('.sops.yaml'):
        parser.error('The file must end in .sops.yaml so the repository creation rule encrypts it.')

    environment = os.environ.copy()
    if args.cluster_age_key:
        environment['SOPS_AGE_KEY'] = age_identity()

    values = {}
    if args.file.exists():
        previous = subprocess.run(['sops', '--decrypt', '--output-type', 'json', str(args.file)],
                                  env=environment, check=True, capture_output=True)
        document = json.loads(previous.stdout)
        if (document['metadata']['namespace'], document['metadata']['name']) != (args.namespace, args.name):
            parser.error(f'{args.file} holds {document["metadata"]["namespace"]}/{document["metadata"]["name"]}.')
        values = document.get('stringData', {})

    for spec in args.keys:
        key, _, source = spec.partition('=@')
        value = Path(source).read_text() if source else getpass.getpass(f'{args.name} {key}: ').strip()
        if not value.strip():
            parser.error(f'{key} is empty.')
        values[key] = value

    secret = {'apiVersion': 'v1', 'kind': 'Secret', 'type': 'Opaque',
              'metadata': {'name': args.name, 'namespace': args.namespace}, 'stringData': values}
    encrypted = subprocess.run(
        ['sops', '--encrypt', '--filename-override', str(args.file), '--input-type', 'json',
         '--output-type', 'yaml', '/dev/stdin'],
        input=json.dumps(secret).encode(), env=environment, check=True, capture_output=True).stdout
    args.file.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=args.file.parent, prefix='.sops-', delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(encrypted)
            handle.close()
            os.replace(temporary, args.file)
        finally:
            temporary.unlink(missing_ok=True)
    print(f'Saved {", ".join(sorted(values))} in {args.file} (encrypted).')


if __name__ == '__main__':
    main()
