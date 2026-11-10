# Longhorn storage

vecna has two Longhorn disks, chosen by tag:

| Disk | Path | Tag | Class | For |
| --- | --- | --- | --- | --- |
| `default-disk-…` | `/var/lib/longhorn/` (NVMe) | `ssd` | `longhorn` (default) | Everything with random I/O: Home Assistant, Zigbee2MQTT, Mosquitto, game databases, Minecraft |
| `bulk0` | `/mnt/bulk0` (4 TB IronWolf, 5400 rpm) | `hdd` | `longhorn-hdd` | Large, rebuildable or append-mostly data |

The default class selects `ssd` (`persistence.defaultDiskSelector` in `helmrelease.yaml`), so a
new volume never lands on the spinning disk by accident. `longhorn-hdd` has one replica, `Retain`,
and sits outside the `daily-snapshot` group.

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
changed. The backups go to the R2 bucket `vecna-backup` in Cloudflare's EU
jurisdiction, encrypted before they leave vecna:

```
Longhorn ──S3──▶ backup-crypt (rclone serve s3 + crypt) ──S3──▶ R2 vecna-backup
```

- `backup-crypt.yaml`: the rclone gateway. Longhorn's target is `s3://longhorn@auto/`
  at the gateway (`backup-gateway.sops.yaml`); the gateway encrypts contents and names
  (rclone crypt) and writes to the bucket. Cloudflare only holds ciphertext.
  `rclone serve s3` is experimental upstream, so a restore is tested after changes.
- `backup-target.sops.yaml`: the R2 token (this bucket only) and endpoint.
- `backup-crypt.sops.yaml`: the crypt passwords, rclone-obscured. **Without these and
  the SOPS age key the backups cannot be read.** Keep the age key outside vecna.
- Not backed up: `longhorn-hdd` volumes (`bulk-none`: the ashes map, rebuilt weekly from
  OSM), Prometheus (`no-snapshots`), and the `snapshot-only` volumes below. Detached
  volumes are skipped.

### Restoring

A volume, with vecna up: Longhorn UI > Backup > pick the backup > Restore, then point
the workload's claim at the new volume (or restore in place over a detached volume).

Everything, after losing vecna: rebuild the node and Flux (the SOPS age key is needed
to decrypt this directory), let Longhorn and `backup-crypt` come up, and the backups
reappear in the UI within `pollInterval` (5 minutes). Restore each volume before its
app starts, or scale the app down first.

Without the cluster, rclone alone reads the bucket: configure the `r2` and `crypt`
remotes from the two Secrets (`rclone config` takes the obscured passwords as they are)
and `rclone ls crypt:`.

## Volumes labelled by hand

Longhorn volume labels are not in git. These were changed on 2026-11-10; a recreated
claim comes back in the `default` group and is backed up off-site until relabelled.

| Namespace | Claim | Group | Why |
| --- | --- | --- | --- |
| monitoring | `storage-loki-0` | `snapshot-only` | Logs; 30 days, rebuildable |
| monitoring | `storage-tempo-0` | `snapshot-only` | Traces |
| house | `esp-home-cache` | `snapshot-only` | Build cache |
| house | `home-assistant-whisper-data` | `snapshot-only` | Downloaded speech model |
| house | `home-assistant-piper-data` | `snapshot-only` | Downloaded voice |

```bash
kubectl -n longhorn label volumes.longhorn.io <pv-name> \
  recurring-job-group.longhorn.io/snapshot-only=enabled recurring-job-group.longhorn.io/default-
```
