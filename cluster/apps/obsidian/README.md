# Obsidian: the shared vault

One Obsidian vault on the server, synced to every device by
[Self-hosted LiveSync](https://github.com/vrtmrz/obsidian-livesync) and open to
Hermes through an MCP server.

| Piece | Where | What |
|---|---|---|
| CouchDB | `couchdb.yaml`, `livesync.ini` | The vault's database; LiveSync's required settings in `livesync.ini` |
| Database and users | `setup.sh`, run by the `setup.yaml` Job | Database `vault`; users `obsidian` (the apps) and `mcp` (Hermes's server) |
| Hermes access | `mcp.yaml` | [obsidian-livesync-mcp](https://github.com/adambenhassen/obsidian-livesync-mcp): note tools over MCP |
| Passwords | `secrets.sops.yaml` | `COUCHDB_PASSWORD` (admin), `OBSIDIAN_PASSWORD`, `MCP_PASSWORD` |

The apps sync at `https://obsidian.${DOMAIN}` on the internal Gateway: the LAN, or
the VPN when away. Nothing is public.

## Vault settings that must not change

- **File identity: Legacy.** The MCP server's bundled LiveSync CLI predates
  LiveSync's NFC identity, which new vaults use by default. Mismatched, it skips
  or duplicates notes.
- **End-to-end encryption and path obfuscation: off.** The database and the MCP
  server's plain copy sit on the same disk, so encryption would protect nothing
  here, and the MCP server would need the passphrase. Turning either on later
  means a rebuild of every device and `mcp.yaml`.

## Setting up a device

The first device creates the vault; the rest copy its settings with a Setup URI.

1. Install **Self-hosted LiveSync** from Obsidian's community plugins.
2. First device only: choose manual setup and enter
   - URI `https://obsidian.${DOMAIN}`, database `vault`, user `obsidian`;
   - password: `kubectl -n obsidian get secret couchdb -o jsonpath='{.data.OBSIDIAN_PASSWORD}' | base64 -d | pbcopy`;
   - end-to-end encryption off, path obfuscation off;
   - **General Settings > File identity: Legacy**.
   Then **Copy setup URI** (it asks for a passphrase that protects the URI only).
3. Other devices: **Use a setup URI**, paste it and its passphrase. Away from home
   the phone syncs while the VPN is on.

## Hermes

Hermes reaches the MCP server at `http://livesync-mcp.obsidian.svc:8765/mcp` with
read and write on every note (`hermes/managed/config.yaml`). Telegram and the CLI
have the tools; Ada's voice and the alert webhook do not. Only the Hermes pod can
reach the server, and the server can reach only CouchDB (`networkpolicy.yaml`): it
is a single maintainer's unlicensed code, so it gets no other network access.

Deletions are soft (LiveSync marks a note deleted) and Longhorn's daily snapshots
cover `couchdb-data`, so an unwanted edit can be undone: in Obsidian from the
note's history, or by restoring the volume.

## Notes

- Changing `livesync.ini` needs a restart: `kubectl -n obsidian rollout restart deploy/couchdb`.
- `setup.sh` is safe to re-run; Flux replaces the Job when it or the Secret changes.
