# Hermes in Agent Sandbox

Hermes replaces the OpenClaw instance, operator, Home Assistant bridge, OpenAI
hostname override and dedicated Whisper HTTP service. Home Assistant's Wyoming
voice services remain. Its existing OpenAI conversation integration must be
disabled or reconfigured in Home Assistant before using that voice pipeline again.

This follows the [upstream Hermes Sandbox example](https://agent-sandbox.sigs.k8s.io/docs/use-cases/examples/hermes-agent/).
The controller and CRD are vendored from Agent Sandbox v1.0.7. Hermes uses
`nousresearch/hermes-agent:v0.22.2`, pinned by its multi-platform image digest.
`cluster/base/agent-sandbox.yaml` waits for the controller before the apps reconcile.

Hermes stores its home and workspace on a 20 GiB Longhorn volume. An init container
copies the Git-managed `config.yaml` into that volume on every pod start. Edit the
source config here, then recreate the pod after reconciliation to apply changes.
The initial model is `google/gemini-3-flash-preview` through OpenRouter, matching the
previous provider/model choice. No previous provider keys or channel tokens are reused.

## Create the new key

Create a dedicated key at [OpenRouter keys](https://openrouter.ai/settings/keys).
Set the spending limit on the key there. From the repo root, run:

```sh
python3 scripts/configure-hermes-secret.py
# Or use Flux's existing age identity from the current Kubernetes context:
python3 scripts/configure-hermes-secret.py --cluster-age-key
# Or read a key you saved locally, outside this checkout:
python3 scripts/configure-hermes-secret.py --key-file /absolute/path/to/key
```

The helper prompts without echo and encrypts directly through SOPS. Plaintext
credentials never go into a temporary file. Configure your age identity as described
in the root README, or set `SOPS_AGE_KEY_FILE`. The helper preserves the separate
gateway API key when updating the OpenRouter credential.

The encrypted Secret must contain both `OPENROUTER_API_KEY` and the separate
`API_SERVER_KEY`. Kubernetes refuses to start the Hermes container if either key
is missing. Run the helper before publishing a newly created Secret.

## Retire OpenClaw without deleting its data

The manifests in `../retained-data` keep the old namespaces and three PVCs. They
disable Flux pruning of those objects. The old operator must finish deleting its
instance **before** Flux removes the operator HelmRelease. Do this before publishing
the migration, while the old operator is still running:

```sh
kubectl -n openclaw patch openclawinstance home-ops-openclaw --type=merge \
  -p '{"spec":{"storage":{"persistence":{"orphan":true}}}}'

# Keep the backing volumes even if a PVC is accidentally removed during cutover.
for claim in home-ops-openclaw-data home-ops-openclaw-chromium-data whisper-stt-cache; do
  volume=$(kubectl -n openclaw get pvc "$claim" -o jsonpath='{.spec.volumeName}')
  kubectl patch pv "$volume" --type=merge \
    -p '{"spec":{"persistentVolumeReclaimPolicy":"Retain"}}'
  kubectl -n openclaw annotate pvc "$claim" \
    kustomize.toolkit.fluxcd.io/prune=disabled --overwrite
done
kubectl annotate namespace openclaw openclaw-operator-system \
  kustomize.toolkit.fluxcd.io/prune=disabled --overwrite

kubectl -n openclaw delete openclawinstance home-ops-openclaw --wait=true --timeout=180s

# The operator may delete its browser PVC even with persistence.orphan enabled.
# Its backing PV was protected above; restore the claim against that same PV.
if ! kubectl -n openclaw get pvc home-ops-openclaw-chromium-data >/dev/null 2>&1; then
  kubectl patch pv pvc-5a0766f5-8e48-4286-b37e-096687da4cb1 --type=merge \
    -p '{"spec":{"claimRef":null}}'
  kubectl apply --server-side -k cluster/apps/retained-data
fi
kubectl -n openclaw get pvc
```

If instance deletion times out, inspect the operator and its finalizer before
continuing. Do not remove the operator first or force namespace deletion.
The retained PVC manifests pin the original PV identities, preventing empty
replacement volumes. Old data is retained for a separate, explicit data cleanup. Old credentials are
removed from desired state; revoke provider and channel credentials separately if
they are no longer used elsewhere.

## Reconcile and verify

Run `python3 scripts/verify-cluster.py` first. Publish the changes to `main` using
the usual Git workflow, then repair/reconcile Flux using the instructions in
`../../README.md`. Flux will remove the retired workloads and encrypted Secrets,
install the Agent Sandbox controller, and create the Hermes Sandbox.

```sh
flux reconcile source git flux-system -n flux-system
flux reconcile kustomization flux-system -n flux-system
flux reconcile kustomization base -n flux-system
flux reconcile kustomization crds -n flux-system
flux reconcile kustomization agent-sandbox -n flux-system
flux reconcile kustomization apps -n flux-system
kubectl -n hermes get sandbox,pod,pvc
kubectl -n hermes wait --for=condition=Ready pod/hermes --timeout=600s
kubectl -n hermes port-forward pod/hermes 8642:8642
```

Check the old namespaces after reconciliation. The legacy bridge was installed
outside Flux's inventory in this cluster, so it needed explicit removal:

```sh
kubectl -n openclaw delete deployment/openclaw-bridge service/openclaw-bridge \
  configmap/bridge-runtime-configmap secret/openclaw-bridge-secrets \
  networkpolicy/home-ops-openclaw-allow-house-voice --ignore-not-found
kubectl -n openclaw-operator-system wait --for=delete helmrelease/openclaw-operator --timeout=180s
kubectl -n openclaw get pods,pvc
```

In another terminal:

```sh
python3 scripts/verify-hermes.py
```

That script checks health and rejects unauthenticated requests, then sends one
small paid model request through Hermes. It reads the API key from the Kubernetes
Secret in memory without printing it. For interactive terminal chat:

```sh
kubectl -n hermes exec -it hermes -c hermes -- hermes chat
```

The API has no Ingress, and NetworkPolicy denies incoming pod traffic. Use a
localhost port-forward. Dashboard and messaging channels are not configured yet.
The pod has no Kubernetes service-account token, host mounts or container socket.
Egress permits cluster DNS and public IPv4 HTTPS, excluding private and link-local
networks. This allows OpenRouter and upstream runtime downloads; it is not an
OpenRouter-only hostname allowlist. Agent Sandbox manages pod and volume lifecycle.
This cluster uses its normal container runtime, with no gVisor/Kata RuntimeClass.
The upstream image bootstraps as root and drops Hermes services to UID 10000.
