# Longhorn storage

vecna has two Longhorn disks, chosen by tag:

| Disk | Path | Tag | Class | For |
| --- | --- | --- | --- | --- |
| `default-disk-…` | `/var/lib/longhorn/` (NVMe) | `ssd` | `longhorn` (default), `longhorn-scratch` | Everything with random I/O: Home Assistant, Zigbee2MQTT, Mosquitto, game databases, Minecraft |
| `bulk0` | `/mnt/bulk0` (4 TB IronWolf, 5400 rpm) | `hdd` | `longhorn-hdd`, `longhorn-hdd-scratch` | Large, rebuildable or append-mostly data |

The default class selects `ssd` (`persistence.defaultDiskSelector` in `helmrelease.yaml`), so a
new volume never lands on the spinning disk by accident. `longhorn-hdd` has one replica, `Retain`,
and sits outside the `daily-snapshot` group. For job scratch claims (the Ashes map rebuild) use `longhorn-scratch` (SSD) or
`longhorn-hdd-scratch`: both delete the volume with its claim and are never snapshotted
or backed up. On `longhorn` a scratch volume still attached at 03:00/03:30 is
snapshotted and sent off-site.

## Volumes moved to the hdd by hand

These existed before `longhorn-hdd`, and a StatefulSet's volume claim template can't change
class, so they were moved on 2026-11-02 by setting the Longhorn volume's `diskSelector` to
`hdd` (`scripts/longhorn-move-volume.sh`). **Git does not record this.** If one of these claims
is deleted and recreated, it comes back on the ssd; move it again with the script.

| Namespace | Claim | Why on hdd |
| --- | --- | --- |
| monitoring | `prometheus-kube-prometheus-stack-prometheus-db-…-0` | Mostly sequential TSDB writes; 21 GB |
| monitoring | `storage-loki-0` | Append-only logs |
| monitoring | `storage-tempo-0` | Append-only traces |
| house | `esp-home-cache` | Build cache; slower firmware builds are fine |

Prometheus is also out of the daily snapshots (Longhorn volume label
`recurring-job-group.longhorn.io/no-snapshots=enabled` in place of `default`): its churn made
7 snapshots cost 40 GB, and nobody restores metrics from a snapshot. Re-apply the label if the
volume is recreated.

## Settings to know

- `storage-minimal-available-percentage` is 25 (cluster-wide): Longhorn won't place a replica on
  a disk that would be left under 25 % free, so about 2.95 TB of `bulk0` is allocatable.
- `bulk0` reserves 0 bytes; the 25 % floor is the margin.
- `replica-soft-anti-affinity` stays `false`. The move script turns it on for the move (it needs
  two replicas on one node for a moment) and back off after.

## Off-site backups

Every night at 03:30 Longhorn backs up the volumes in the `default` group
(`recurring-jobs.yaml`, `daily-backup`), keeps 14, and uploads only the blocks that
changed. The target is the R2 bucket `vecna-backup` in Cloudflare's EU jurisdiction
(`s3://vecna-backup@auto/`); `backup-target.sops.yaml` holds its endpoint and a token
for that bucket only.

- Encryption at rest is Cloudflare's, with keys Cloudflare manages. R2 has no
  customer-managed keys, and Longhorn cannot send the per-request keys of SSE-C, so
  client-side encryption would need a gateway in front of the bucket.
- Not backed up: `longhorn-hdd` volumes (`bulk-none`: the ashes map, rebuilt weekly from
  OSM), Prometheus (`no-snapshots`), the scratch classes, and the `snapshot-only` volumes below. Detached
  volumes are skipped.

### Restoring

A volume, with vecna up: Longhorn UI > Backup > pick the backup > Restore, then point
the workload's claim at the new volume (or restore in place over a detached volume).

Everything, after losing vecna: rebuild the node and Flux (the SOPS age key is needed
to decrypt the token), let Longhorn come up, and the backups reappear in the UI within
`pollInterval` (5 minutes). Restore each volume before its app starts, or scale the
app down first. Keep the age key outside vecna.

## Volumes labelled by hand

Longhorn volume labels are not in git. These were changed on 2026-11-10 and 2026-11-11; a recreated
claim comes back in the `default` group and is backed up off-site until relabelled.

| Namespace | Claim | Group | Why |
| --- | --- | --- | --- |
| monitoring | `storage-loki-0` | `snapshot-only` | Logs; 30 days, rebuildable |
| monitoring | `storage-tempo-0` | `snapshot-only` | Traces |
| house | `esp-home-cache` | `snapshot-only` | Build cache |
| house | `home-assistant-whisper-data` | `snapshot-only` | Downloaded speech model |
| house | `home-assistant-piper-data` | `snapshot-only` | Downloaded voice |
| ashes-dev | `game-db-1` | `snapshot-only` | Dev database; only prod is backed up off-site |

```bash
kubectl -n longhorn label volumes.longhorn.io <pv-name> \
  recurring-job-group.longhorn.io/snapshot-only=enabled recurring-job-group.longhorn.io/default-
```
