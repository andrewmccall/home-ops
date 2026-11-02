# AGENTS

Flux GitOps for the k3s cluster on vecna: `cluster/` is applied by Flux, `ansible/` sets up hosts.
Cluster setup and DNS domain: `cluster/README.md`.

- **Storage.** Before adding or changing a PersistentVolumeClaim, StorageClass or anything Longhorn,
  read `cluster/core/longhorn/README.md`: which disk each class uses, and volumes moved to the
  hdd by hand that git does not record.
- **Check before committing.** `python scripts/verify-releases.py --base origin/main` renders every
  HelmRelease and fails on errors Flux would hit; CI runs it as `validate`.
