# Obsidian: the shared vault

One Obsidian vault on the server, synced to every device by
[Self-hosted LiveSync](https://github.com/vrtmrz/obsidian-livesync), and open to
Hermes as plain Markdown files.

| Piece | Where | What |
|---|---|---|
| CouchDB | `couchdb.yaml`, `livesync.ini` | The vault's database; LiveSync's required settings in `livesync.ini` |
| Database | `setup.sh`, run by the `setup.yaml` Job | Database `vault` |
| Users | `couchdb.yaml` (init container) | `obsidian` (the apps) and `bridge` are CouchDB server admins: LiveSync deletes and recreates the database when it initialises or rebuilds a vault, which wipes per-database permissions |
| Hermes's copy | `bridge/` (in the `hermes` namespace) | [livesync-bridge](https://github.com/vrtmrz/livesync-bridge) syncs the database with the `obsidian-vault` volume, both ways |
| Passwords | `secrets.sops.yaml`, `bridge/config.sops.yaml` | `COUCHDB_PASSWORD` (admin), `OBSIDIAN_PASSWORD`, `BRIDGE_PASSWORD` (also in the bridge's config) |

The apps sync at `https://obsidian.${DOMAIN}` on the internal Gateway: the LAN, or
the VPN when away. Nothing is public.

## Vault settings

- **File identity: Unicode NFC**, LiveSync's default for a new vault. The bridge
  is configured to match (`pathNormalizationVersion: 1`); a device on Legacy
  identity would see duplicated or missing notes.
- **End-to-end encryption and path obfuscation: off.** The database and Hermes's
  plain copy sit on the same disk, so encryption would protect nothing here, and
  the bridge would need the passphrase. Turning either on later means rebuilding
  every device and the bridge's config.

## Setting up a device

The first device creates the vault; the rest copy its settings with a Setup URI.

1. Install **Self-hosted LiveSync** from Obsidian's community plugins.
2. First device only: choose manual setup and enter
   - URI `https://obsidian.${DOMAIN}`, database `vault`, user `obsidian`;
   - password: `kubectl -n obsidian get secret couchdb -o jsonpath='{.data.OBSIDIAN_PASSWORD}' | base64 -d | pbcopy`;
   - end-to-end encryption off, path obfuscation off.
   Then **Copy setup URI** (it asks for a passphrase that protects the URI only).
3. Other devices: **Use a setup URI**, paste it and its passphrase. Away from home
   the phone syncs while the VPN is on.

## Hermes

Hermes sees the vault at `/opt/data/workspace/vault` (`hermes/sandbox.yaml`), read
and write, and works on it with its own file and terminal tools: search, bulk edits,
scripts. A change there reaches every device through the bridge within seconds, and
a change on a device reaches the files the same way. Telegram and the CLI have
those tools; Ada's voice and the alert webhook do not.

A note edited in Obsidian and by Hermes at the same moment becomes a LiveSync
conflict, which Obsidian shows for you to resolve. Deletions are soft (LiveSync
marks a note deleted), and Longhorn's daily snapshots cover both volumes, so an
unwanted edit can be undone from the note's history in Obsidian or by restoring a
volume.

### The bridge

livesync-bridge publishes no image or release. The pod runs the official Deno
image; its init container (`bridge/install.sh`) downloads the pinned commit and its
locked dependencies onto `livesync-bridge-state` once, so restarts need no internet.
To move the commit, change `BRIDGE_COMMIT` and `workingDir` in `bridge/bridge.yaml`
to a commit at least 7 days old.

## Agents and folders

CouchDB permissions are per database, so inside one vault a folder is not a
boundary: any CouchDB user can read every note. Agents never get CouchDB access,
only a view of the files, and the view is what limits them.

Lay the vault out so agents can be given part of it later:

| Folder | For |
|---|---|
| your own folders | Notes only you and Hermes see |
| `Shared/` | Notes meant for agents |
| `Agents/<name>/` | Each agent's own workspace |

- **Hermes** sees the whole vault.
- **Another agent** (a Hermes subagent with its own pod, a Sproozi run) gets a mount
  of only its folder: a `subPath` of the vault volume, which the kernel enforces.
  Telling an agent to stay in a folder is a convention, not a guard.
- **A hard wall** (even compromised sync code cannot read your notes) needs a
  separate vault: its own CouchDB database. Obsidian cannot link across vaults.

## Notes

- Changing `livesync.ini` needs a restart (an init container copies it in): `kubectl -n obsidian rollout restart deploy/couchdb`.
- `setup.sh` is safe to re-run; Flux replaces the Job when it or the Secret changes.
