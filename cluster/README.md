## :construction: Installation

Create namespace
```bash
kubectl create namespace flux-system
```

Add SOPS private key
```bash

kubectl -n flux-system create secret generic sops-age \
  --from-file=age.agekey=sops-key.txt
```

Genrate a key
```
flux create secret git flux-cluster \
    --url=ssh://git@github.com/andrewmccall/home-ops
  ```

put the key as a deploy key in github

Install Flux
```bash

flux bootstrap git \
  --url=ssh://git@github.com/andrewmccall/home-ops.git \
  --branch=main \
  --private-key-file=../key \
  --path=cluster/flux-system/ \
  --cluster-domain=cluster.andrewmccall.com
```

Enable k3s upgrades (if not already done by ansible)
`
kubectl label node --all k3s-upgrade=true
```

The CloudNativePG operator is a Flux HelmRelease in `core/cloudnative-pg/`; no manual
install is needed. Its README has the runbook for adopting a hand-installed operator.

## Updates and maintenance windows

Renovate opens and automerges dependency PRs; Flux applies a merge within minutes.
All times are Europe/London.

| What | When it lands | Why |
|---|---|---|
| Most updates (Helm charts, GitHub releases, Ansible collections, most Docker Hub images) | Nightly, 00:00-06:00, once the release is **7 days old** | The cooldown gives a compromised release time to be caught and pulled. No PR exists before then; the Renovate Dashboard issue lists what is waiting. |
| Images Renovate cannot date (see below) | **Sunday 00:00-06:00** (Saturday night), any age | No release date means no cooldown, so they are batched where Sunday shows any breakage before the k3s upgrade. |
| k3s patch releases | **Monday 01:00-04:00** (Sunday night), only if the cluster is healthy | A day after the image batch. The upgrade job first checks that nodes, every Flux Kustomization and HelmRelease are Ready and no warning or critical alert is firing (house device alerts aside), and otherwise does nothing. |
| k3s minor releases (e.g. 1.37 to 1.38) | When a person merges the PR | Check that Calico supports the new Kubernetes minor first (`ansible/roles/calico/defaults/main.yml`). Then it lands in the next Monday window. |
| Our own images and charts, Minecraft Bedrock | Bedrock at any time, ours nightly, no cooldown | We publish ours. Bedrock clients update themselves and cannot join an older server. |
| Longhorn and CloudNativePG minors, any major | When a person merges the PR | Each needs its own care; see the comments in `renovate.json5`. |

Renovate gets release dates only from Docker Hub's tag API, and only for repositories
under its 1,000-tag anonymous paging limit. Home Assistant, ESPHome and code-server
(nightly dev builds put them over), Music Assistant, the UniFi webhook (ghcr.io only)
and agent-sandbox (registry.k8s.io) are undated, so they use the Sunday batch. When
adding an image, prefer the project's own Docker Hub repository; a ghcr.io-only image
goes in the Sunday list in `renovate.json5`.

The policy lives in the comments of `renovate.json5`, and the k3s window and health
check in `cluster/core/system-upgrade/server-plan.yaml`.

### Watching or holding a k3s upgrade

```bash
kubectl -n system-upgrade get plan k3s-server    # target version and status message
kubectl -n system-upgrade get jobs               # one job per attempt
kubectl -n system-upgrade logs job/<name> -c prepare   # "NOT UPGRADING: ..." names the problem
```

The health check reads live alerts, so a firing warning holds the upgrade until
it clears. To skip a week on purpose, leave the Renovate PR unmerged; once it is
merged, set `version` in `server-plan.yaml` back to the running version
(`kubectl get nodes` shows it).

## Cluster DNS domain

This k3s cluster uses `cluster.andrewmccall.com`. CoreDNS's `kubernetes` zone and
the kubelet's pod DNS search suffixes use that domain. Kubernetes defaults to
`cluster.local` in many generators; it is incorrect for this cluster.

Always pass `--cluster-domain=cluster.andrewmccall.com` to `flux bootstrap` or
`flux install --export` when regenerating Flux components. Keep the Kustomize
patches in `flux-system/flux-system/kustomization.yaml` aligned with the generated
arguments. They change the event and source artifact addresses without editing
`gotk-components.yaml`. A further patch raises the generated `flux-system`
GitRepository interval from 1m to 30m, because GitHub webhooks trigger fetches
([polling intervals](core/flux-system/webhook/README.md#polling-intervals)). Each
patch tests the original value first so generator changes fail visibly instead of
overwriting a different flag.

Run this after changing manifests:

```sh
python3 scripts/verify-cluster.py
```

The check renders all Flux entry points and rejects `cluster.local`, including
new manifests. It also checks the actual controller addresses. The GitHub workflow
`Validate cluster manifests` runs the same command for PRs and pushes to main.
Application configurations should use `service.namespace.svc` for in-cluster DNS
when a full absolute DNS name is unnecessary.

The root `flux-system/kustomization.yaml` includes the generated controller overlay
and a Flux `base` Kustomization. That Kustomization manages `cluster/base`, including
the app/controller dependency definitions and SOPS-encrypted cluster settings.
Keep this link when regenerating bootstrap manifests.

### Recover Flux from the wrong artifact hostname

On 2026-10-17 the running source-controller advertised
`source-controller.flux-system.svc.cluster.local.`. Flux could fetch Git, but other
controllers could not resolve its artifact URLs, so CRDs, core and apps stopped
reconciling. Correcting only an app Service URL cannot repair that failure.

After publishing the validated domain fix on main, repair the live address
arguments so Flux can recover without first needing its broken artifact URL.
The helper preserves all other arguments and tests the observed value before
patching, so a concurrent update causes a failure. Its default is a server dry run:

```sh
python3 scripts/repair-flux-domain.py
python3 scripts/repair-flux-domain.py --apply
kubectl -n flux-system rollout status deployment/source-controller --timeout=120s
kubectl -n flux-system rollout status deployment/kustomize-controller --timeout=120s
kubectl -n flux-system rollout status deployment/helm-controller --timeout=120s
flux reconcile source git flux-system -n flux-system
kubectl -n flux-system get gitrepositories,kustomizations
```

Do not reapply the whole generated Flux bundle just to repair DNS. Review any
controller version changes as a Flux upgrade. Before reconciling an upgrade, run
[`flux migrate`](https://fluxcd.io/flux/cmd/flux_migrate/) against the cluster to
migrate stored custom-resource versions. During this cutover, a stored notification
Provider `v1beta2` prevented the new CRD from applying until migration completed.
`flux migrate -f cluster --dry-run` checks whether the repository also needs API
version updates.

Recovering Flux resumes deployment of the current contents of main. For the Hermes
migration, first complete the credential and data-retention steps in the
[cutover guide](apps/hermes/README.md). Then reconcile the Flux, CRD, controller
and app Kustomizations in that guide's order.
