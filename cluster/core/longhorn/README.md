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
