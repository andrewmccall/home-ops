# CloudNativePG operator

`helmrelease.yaml` installs the [CloudNativePG](https://cloudnative-pg.io) operator into
`cnpg-system` from the official chart. The game's Postgres `Cluster`s
(`ashes-dev/game-db`, `ashes-map/map-db`) depend on it.

| Chart | Operator | Why this version |
| --- | --- | --- |
| `cloudnative-pg` 0.29.1 | 1.30.1 | PostgreSQL 18 support arrived in operator 1.27.1; 1.30.1 is the newest release and also fixes PG18-specific issues (checksums default, metrics scraping). |

The chart owns the CRDs (`crds.create: true`). They carry `helm.sh/resource-policy: keep`, so
uninstalling the release or deleting the HelmRelease leaves CRDs and `Cluster`s in place. The
release opts out of automatic rollback (`remediation: manual`): CloudNativePG does not support
operator downgrades.

Every operator upgrade restarts each Postgres instance once to update its instance manager. With
one instance per Cluster, that means a short database outage; clients must reconnect.

## Adopting the hand-installed operator

Until this release, the operator came from
`kubectl apply --server-side -f .../release-1.26/releases/cnpg-1.26.0.yaml`. The chart
can adopt the objects whose names match. Others must be deleted:

| Object (1.26.0 manifest) | Chart object | Action |
| --- | --- | --- |
| 9 CRDs `*.postgresql.cnpg.io` | same names | adopt; upgraded to 1.30 schemas; two new CRDs added (`databaseroles`, `failoverquorums`) |
| MutatingWebhookConfiguration `cnpg-mutating-webhook-configuration` | same | adopt |
| ValidatingWebhookConfiguration `cnpg-validating-webhook-configuration` | same | adopt |
| Service `cnpg-webhook-service` | same | adopt (selector gains `app.kubernetes.io/instance`) |
| ConfigMap `cnpg-default-monitoring` | same | adopt |
| Deployment `cnpg-controller-manager` | same name, **different selector** | delete; `spec.selector` is immutable |
| ServiceAccount `cnpg-manager` | `cnpg-controller-manager` | delete |
| ClusterRole `cnpg-manager` | `cnpg-controller-manager` | delete |
| ClusterRoleBinding `cnpg-manager-rolebinding` | `cnpg-controller-manager` | delete |
| ClusterRoles `cnpg-{database,publication,subscription}-{editor,viewer}-role` | `cnpg-controller-manager-{edit,view}` | delete (nothing binds them) |
| Namespace `cnpg-system` | not in chart; `namespace.yaml` | Flux applies it in place |

Secrets `cnpg-ca-secret` and `cnpg-webhook-cert` belong to the operator, not the manifest; keep
them. The new operator reuses them.

Do steps 1-3 **before merging** the PR that adds this directory. Once Flux sees the HelmRelease,
Helm refuses objects that lack its ownership metadata. It also cannot change the old Deployment's
selector. Postgres keeps running without the operator. While the operator is down, its webhooks
(`failurePolicy: Fail`) reject creating or changing CNPG objects. Flux retries.

```sh
NS=cnpg-system RELEASE=cloudnative-pg

# 0. Pre-flight: hand-installed 1.26.0, no Helm release yet, both Clusters healthy.
kubectl -n $NS get deploy cnpg-controller-manager -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
helm -n $NS list
kubectl get clusters.postgresql.cnpg.io -A

# 1. Mark the same-named objects as owned by the Helm release so Helm adopts them.
for obj in $(kubectl get crd -o name | grep '\.postgresql\.cnpg\.io$') \
    mutatingwebhookconfiguration/cnpg-mutating-webhook-configuration \
    validatingwebhookconfiguration/cnpg-validating-webhook-configuration \
    service/cnpg-webhook-service \
    configmap/cnpg-default-monitoring; do
  kubectl -n $NS label --overwrite "$obj" app.kubernetes.io/managed-by=Helm
  kubectl -n $NS annotate --overwrite "$obj" \
    meta.helm.sh/release-name=$RELEASE meta.helm.sh/release-namespace=$NS
done

# 2. Stop the old operator (its Deployment selector cannot be changed in place).
kubectl -n $NS delete deployment/cnpg-controller-manager --wait=true

# 3. Remove the old RBAC whose names differ from the chart's.
kubectl -n $NS delete serviceaccount/cnpg-manager
kubectl delete clusterrolebinding/cnpg-manager-rolebinding clusterrole/cnpg-manager \
  clusterrole/cnpg-database-editor-role clusterrole/cnpg-database-viewer-role \
  clusterrole/cnpg-publication-editor-role clusterrole/cnpg-publication-viewer-role \
  clusterrole/cnpg-subscription-editor-role clusterrole/cnpg-subscription-viewer-role

# 4. Merge the PR, then pull it in now rather than waiting for the interval.
flux reconcile source git flux-system -n flux-system
flux reconcile kustomization base -n flux-system     # HelmRepository cloudnative-pg
flux reconcile kustomization core -n flux-system     # Namespace + HelmRelease
flux get helmreleases -n $NS --watch                 # until Ready=True
```

If the install fails (manual remediation means no retries), fix the cause and retry with
`flux reconcile helmrelease cloudnative-pg -n cnpg-system --force`.

### Verify

```sh
kubectl -n cnpg-system rollout status deployment/cnpg-controller-manager --timeout=5m
kubectl -n cnpg-system get deploy cnpg-controller-manager -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'   # ...:1.30.1
helm -n cnpg-system list                                                   # cloudnative-pg-0.29.1, deployed
kubectl get crd clusters.postgresql.cnpg.io -o jsonpath='{.metadata.labels.app\.kubernetes\.io/managed-by}{"\n"}'  # Helm
# The instance pods restart once onto the 1.30.1 instance manager; wait for both Clusters.
kubectl -n ashes-dev wait cluster.postgresql.cnpg.io/game-db --for=condition=Ready --timeout=10m
kubectl -n ashes-map wait cluster.postgresql.cnpg.io/map-db --for=condition=Ready --timeout=10m
kubectl get clusters.postgresql.cnpg.io -A                                 # "Cluster in healthy state"
kubectl cnpg status game-db -n ashes-dev                                   # if the cnpg plugin is installed
kubectl cnpg status map-db -n ashes-map
# Nothing from the old install is left running or bound:
kubectl get sa -n cnpg-system; kubectl get clusterrole,clusterrolebinding | grep cnpg
```

### Roll back

Operator downgrades are unsupported. Older operators do not understand newer CRD fields or
PostgreSQL 18 Clusters (PG18 needs 1.27.1 or later). Rolling forward is safer. Roll back only to
undo a failed cut-over while both Clusters are still disposable PostgreSQL 17:

```sh
NS=cnpg-system
flux suspend helmrelease cloudnative-pg -n $NS     # core has prune: false, so a revert alone removes nothing
kubectl -n $NS delete deployment/cnpg-controller-manager      # chart selector differs from the manifest's
kubectl apply --server-side --force-conflicts -f \
  https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.26/releases/cnpg-1.26.0.yaml
kubectl -n $NS delete serviceaccount/cnpg-controller-manager configmap/cnpg-controller-manager-config
kubectl delete clusterrolebinding/cnpg-controller-manager clusterrole/cnpg-controller-manager \
  clusterrole/cnpg-controller-manager-view clusterrole/cnpg-controller-manager-edit
kubectl -n $NS delete secret -l owner=helm,name=cloudnative-pg   # forget the Helm release
kubectl get clusters.postgresql.cnpg.io -A
```

Then revert the PR. The 1.26.0 manifest restores the old CRD schemas. The `databaseroles` and
`failoverquorums` CRDs remain, unused.
