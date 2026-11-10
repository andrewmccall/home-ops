# AGENTS

Flux GitOps for the k3s cluster on vecna: `cluster/` is applied by Flux, `ansible/` sets up hosts.
Cluster setup and DNS domain: `cluster/README.md`.

- **Storage.** Before adding or changing a PersistentVolumeClaim, StorageClass or anything Longhorn,
  read `cluster/core/longhorn/README.md`: which disk each class uses, and volumes moved to the
  hdd by hand that git does not record.
- **Postgres.** The CloudNativePG operator and its CRDs come from the HelmRelease in
  `cluster/core/cloudnative-pg/`. Read its README before upgrading the operator: each upgrade
  restarts every Postgres instance, and downgrades are unsupported.
- **Monitoring.** Before adding a dashboard (here or from another repo), alert rule, scrape
  target or log query, or touching Grafana, Prometheus, Alertmanager, Loki or Vector, read
  `cluster/apps/monitoring/README.md`.
- **Dependency updates.** Before adding an image or changing when or how something updates,
  read `cluster/README.md#updates-and-maintenance-windows`: a 7-day release cooldown, nightly
  automerges, a Sunday batch for images Renovate cannot date, and gated k3s upgrades at 01:00
  on Monday. Prefer an image's Docker Hub source.
- **Check before committing.** `python scripts/verify-releases.py --base origin/main` renders every
  HelmRelease and fails on errors Flux would hit; CI runs it as `validate`.
