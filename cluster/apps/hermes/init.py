"""Prepare Hermes's volume before it starts (the Sandbox's init container).

- Seed config.yaml and SOUL.md from Git only when missing: Hermes owns them after.
- Remove from Hermes's config.yaml every setting the managed file pins, so a stale
  copy can never take effect if a pin is later dropped from Git.
- Build the CA bundle and install the alert script and skill (owned by Git).

Paths are arguments' defaults so tests can point them elsewhere.
"""
import os
from pathlib import Path
import shutil
import sys

UID = GID = 10000


def managed_leaves(tree, prefix=()):
    """Dotted paths the managed scope pins: non-empty dicts recurse, anything else is a leaf."""
    for key, value in tree.items():
        if isinstance(value, dict) and value:
            yield from managed_leaves(value, prefix + (key,))
        else:
            yield prefix + (key,)


def prune(config, leaves):
    """Delete each pinned leaf from config, then any parent left empty. Returns removed paths."""
    removed = []
    for path in leaves:
        parents, node = [], config
        for key in path[:-1]:
            if not isinstance(node, dict) or key not in node:
                break
            parents.append((node, key))
            node = node[key]
        else:
            if isinstance(node, dict) and path[-1] in node:
                del node[path[-1]]
                removed.append('.'.join(map(str, path)))
                for parent, key in reversed(parents):
                    if parent[key] == {}:
                        del parent[key]
    return removed


def own(path, root):
    for owned in (path, *path.relative_to(root).parents):
        os.chown(root / owned, UID, GID)


def main(data=Path('/opt/data'), seed=Path('/etc/hermes-seed'), managed=Path('/etc/hermes/config.yaml'),
         sre=Path('/etc/hermes-sre'), trust=Path('/etc/hermes-trust'), bundle=Path('/etc/hermes-ca/ca-bundle.pem'),
         system_roots=Path('/etc/ssl/certs/ca-certificates.crt'), chown=True):
    from ruamel.yaml import YAML  # ships with Hermes; keeps comments in Hermes's own file

    yaml = YAML()
    for name in ('config.yaml', 'SOUL.md'):
        target = data / name
        if not target.exists():
            shutil.copyfile(seed / name, target)
            print(f'seeded {name}')
        if chown:
            os.chown(target, UID, GID)

    user_file = data / 'config.yaml'
    user = yaml.load(user_file.read_text()) or {}
    removed = prune(user, list(managed_leaves(yaml.load(managed.read_text()) or {})))
    if removed:
        with user_file.open('w') as handle:
            yaml.dump(user, handle)
        print('removed pinned settings from config.yaml: ' + ', '.join(removed))

    workspace = data / 'workspace'
    workspace.mkdir(exist_ok=True)
    if chown:
        os.chown(workspace, UID, GID)
        # Alert decisions: Hermes must own them even if a root command wrote them.
        for path in (data / 'sre').glob('*'):
            os.chown(path, UID, GID)

    # The image's public roots plus the private CA of the Sproozi task service.
    bundle.write_text(system_roots.read_text() + (trust / 'sproozi-tasks-ca.crt').read_text())

    # Alert triage: the webhook route's script and its skill.
    for source, target in (('sre_alerts.py', 'scripts/sre_alerts.py'), ('SKILL.md', 'skills/devops/sre-alerts/SKILL.md')):
        path = data / target
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(sre / source, path)
        if chown:
            own(path, data)


if __name__ == '__main__':
    main()
    sys.exit(0)
