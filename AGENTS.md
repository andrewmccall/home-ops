# AGENTS

Flux GitOps for the k3s cluster on vecna: `cluster/` is applied by Flux, `ansible/` sets up hosts.
Cluster setup and DNS domain: `cluster/README.md`.

- **Storage.** Before adding or changing a PersistentVolumeClaim, StorageClass or anything Longhorn,
  read `cluster/core/longhorn/README.md`: which disk each class uses, and volumes moved to the
  hdd by hand that git does not record.
- **Postgres.** The CloudNativePG operator and its CRDs come from the HelmRelease in
  `cluster/core/cloudnative-pg/`. Read its README before upgrading the operator: each upgrade
  restarts every Postgres instance, and downgrades are unsupported.
- **Check before committing.** `python scripts/verify-releases.py --base origin/main` renders every
  HelmRelease and fails on errors Flux would hit; CI runs it as `validate`.
