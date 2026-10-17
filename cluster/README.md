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

Make sure we've got the cloudnative postgres installed.

````bash

kubectl apply --server-side -f \
  https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.26/releases/cnpg-1.26.0.yaml
  ````

## Cluster DNS domain

This k3s cluster uses `cluster.andrewmccall.com`. CoreDNS's `kubernetes` zone and
the kubelet's pod DNS search suffixes use that domain. Kubernetes defaults to
`cluster.local` in many generators; it is incorrect for this cluster.

Always pass `--cluster-domain=cluster.andrewmccall.com` to `flux bootstrap` or
`flux install --export` when regenerating Flux components. Keep the Kustomize
patches in `flux-system/flux-system/kustomization.yaml` aligned with the generated
arguments. They change the event and source artifact addresses without editing
`gotk-components.yaml`. Each patch tests the original argument first so generator
changes fail visibly instead of overwriting a different flag.

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
