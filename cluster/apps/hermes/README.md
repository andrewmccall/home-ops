# Hermes in Agent Sandbox

Hermes replaces the OpenClaw instance, operator, Home Assistant bridge, OpenAI
hostname override and dedicated Whisper HTTP service. Home Assistant's Wyoming
voice services remain. Its existing Ada conversation integration uses the Hermes API.

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

The encrypted Secret must contain `OPENROUTER_API_KEY`, the separate
`API_SERVER_KEY`, and `HOME_ASSISTANT_TOKEN` (see Home Assistant voice below).
Kubernetes refuses to start the Hermes container if a required key is missing.
The OpenRouter helper preserves the other existing credentials.

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

If Home Assistant previously received manual Deployment patches for the bridge,
Helm can preserve those fields after the chart stops rendering them. Once the new
Helm manifest is installed, remove those stale overrides with:

```sh
python3 scripts/cleanup-ha-openclaw-proxy.py
kubectl -n house rollout status deployment/home-assistant --timeout=180s
```

The helper checks the current Helm manifest first and removes only the OpenClaw
hostname alias, proxy CA mounts, CA merge init container and CA environment override.

## Home Assistant voice

Home Assistant's `OPENAI_BASE_URL` points its OpenAI SDK client at
`http://hermes-api.hermes.svc:8642/v1`. The internal Service selects the Hermes pod.
NetworkPolicy allows port 8642 only from the Home Assistant controller in `house`.
The Wyoming voice pod continues to provide Whisper speech recognition and Piper
speech synthesis. Ada's existing pipeline and conversation entity stay in use.
Each speech container mounts its own persistent `/data` cache. The current
Wyoming Whisper image automatically selects Parakeet for English; the first use
downloads that model. The cache keeps it across pod replacements.

Hermes v0.22.2's OpenAI-compatible endpoint does not forward client-supplied tools
to its agent. Home Assistant's tool selection alone therefore cannot give Hermes
device control. Instead, Hermes connects to Home Assistant's native MCP Server.
Configure that integration to expose only the Assist API, using the existing
Assist entity exposure settings, then provision its credential:

```sh
python3 scripts/configure-hermes-ha-mcp.py --cluster-age-key
```

The helper requires the MCP integration to be present and restricted to Assist.
It creates a named **Hermes Assist** token through Home Assistant's supported API
and encrypts it directly into the existing SOPS Secret, retaining the other keys.
It reuses a saved credential on subsequent runs. The token expires after 365 days
and inherits the owner's account permissions; the token itself is not scoped to
MCP. Revoke it in the owner's Security settings before replacing it or retiring
Hermes. No plaintext token is written to disk or printed.

The API platform enables only the Home Assistant MCP toolset, avoiding unrelated
terminal and skill-management calls during voice requests. CLI tools retain their
normal configuration. NetworkPolicy permits Hermes to reach only the Home
Assistant controller on port 8123 inside the private network.

After the endpoint rollout, configure the existing integration and verify Ada:

```sh
python3 scripts/configure-ha-hermes.py --local-commands-first
```

The helper uses Home Assistant's configuration APIs to update the gateway API key
and model. It preserves the existing prompt and exposed-entity API selection. It
reads the gateway credential from Kubernetes and exchanges an existing Home
Assistant owner's refresh token inside the running container. Tokens stay in
memory and are not printed. The key and model persist through Home Assistant's
normal config storage on its PVC.
The optional `--local-commands-first` flag enables Home Assistant's native intent
handler for recognised home commands before falling back to Hermes. Other
requests still use Hermes and OpenRouter. It preserves the rest of the pipeline.

Verification sends one paid text request through the preferred Ada pipeline and
requires both a Hermes response and generated Piper audio. It does not exercise a
physical microphone, satellite wake word, speaker playback or device-control action.

Start a local API tunnel:

```sh
kubectl -n hermes port-forward pod/hermes 8642:8642
```

Leave it running, then verify from another terminal:

```sh
python3 scripts/verify-hermes.py
```

That script checks health and rejects unauthenticated requests, then sends one
small paid model request through Hermes. It reads the API key from the Kubernetes
Secret in memory without printing it. For interactive terminal chat:

```sh
kubectl -n hermes exec -it hermes -c hermes -- hermes chat
```

The API has no Ingress. NetworkPolicy permits the Home Assistant controller and
denies other incoming pod traffic. Use a localhost port-forward for laptop access.
The dashboard and native messaging channels are not configured yet.
The pod has no Kubernetes service-account token, host mounts or container socket.
Egress permits cluster DNS, Home Assistant on port 8123, and public IPv4 HTTPS,
excluding other private and link-local networks. This allows OpenRouter and upstream runtime downloads; it is not an
OpenRouter-only hostname allowlist. Agent Sandbox manages pod and volume lifecycle.
This cluster uses its normal container runtime, with no gVisor/Kata RuntimeClass.
The upstream image bootstraps as root and drops Hermes services to UID 10000.
