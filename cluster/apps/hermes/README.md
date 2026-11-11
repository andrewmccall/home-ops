# Hermes in Agent Sandbox

Hermes replaces the OpenClaw instance, operator, Home Assistant bridge, OpenAI
hostname override and dedicated Whisper HTTP service. Home Assistant's Wyoming
voice services remain. Its existing Ada conversation integration uses the Hermes API.

This follows the [upstream Hermes Sandbox example](https://agent-sandbox.sigs.k8s.io/docs/use-cases/examples/hermes-agent/).
The controller and CRD are vendored from Agent Sandbox v1.0.7. Hermes uses
`nousresearch/hermes-agent:v0.22.2`, pinned by its multi-platform image digest.
`cluster/base/agent-sandbox.yaml` waits for the controller before the apps reconcile.

Hermes stores its home and workspace on a 20 GiB Longhorn volume.

## Who owns the configuration

| File | Owner | How it changes |
| --- | --- | --- |
| `managed/config.yaml` → `/etc/hermes/config.yaml` (read-only) | Git | Hermes's *managed scope*: these settings override Hermes's own and Hermes cannot change them (`hermes config set` refuses; saves drop them). Edit here, then recreate the pod. |
| `/opt/data/config.yaml`, `/opt/data/SOUL.md` | Hermes | `hermes config set`, `hermes setup`, or by asking Ada. Edits persist on the volume. `seed/` holds the first-start copies, used only when a file is missing. |
| `sre/` → script and `sre-alerts` skill | Git | Copied in on every start. |

Pinned: tool limits per platform (voice gets only Home Assistant, alerts only
web tools and Sproozi), the MCP servers, the API, Telegram and webhook platforms,
the terminal backend, secret redaction and command deny rules. Everything else,
including the model, memory, skills and Ada's personality, is Hermes's. The init
container (`init.py`, tested in `tests/test_hermes_init.py`) removes from Hermes's
`config.yaml` any setting Git pins, so a stale copy cannot take over if a pin is
dropped. To start Hermes's own config again, delete `/opt/data/config.yaml` and
recreate the pod.

Run the wizard for Hermes-owned settings; it skips pinned ones:

```sh
kubectl -n hermes exec -it hermes -c hermes -- hermes setup          # or: hermes setup model|agent|tools
```

The assistant is **Ada**: `SOUL.md` is Hermes's identity and style prompt, used by
every platform (voice, Telegram, CLI, alert runs). On Telegram the bot's display
name and picture are set in @BotFather (`/setname`, `/setuserpic`).

The model is Anthropic's `claude-sonnet-5-5`, with a dedicated API key. Home
Assistant names a model in each Ada request and Hermes's API serves it, so after
changing Hermes's model rerun `scripts/configure-ha-hermes.py`; it reads the live
model from the pod.

### Security limits

Hermes runs its terminal locally (`terminal.backend: local`); the pod, with no
Kubernetes token and a NetworkPolicy, is the isolation boundary. Hermes's Docker
and SSH backends are unavailable in this pod. Hermes scrubs known keys from
terminal commands, but a command runs as the gateway's own user and can read the
gateway's environment (`/proc/<pid>/environ`), so **every key in the Secret is
reachable from a Telegram or CLI session that runs commands**. The pinned deny
rules and `HERMES_WRITE_SAFE_ROOT=/opt/data` raise the bar; they do not contain a
determined prompt injection. Alert runs and Ada voice have no terminal or file tools.
Checkpoints are on by default (`/rollback`).

## Credentials

`api-keys.sops.yaml` holds the Secret `hermes-agent-api-keys`:

| Key | What |
| --- | --- |
| `ANTHROPIC_API_KEY` | Hermes's own Anthropic key; set a spending limit on its Console workspace |
| `API_SERVER_KEY` | Bearer key for Hermes's API (Home Assistant uses it) |
| `HOME_ASSISTANT_TOKEN` | Home Assistant MCP token (see Home Assistant voice below) |
| `SPROOZI_TASK_TOKEN` | Bearer token for the Sproozi task service (`../sproozi`) |
| `ALERTMANAGER_WEBHOOK_TOKEN` | Shared with Alertmanager's `hermes-alert-webhook` Secret |
| `TELEGRAM_BOT_TOKEN` | From @BotFather |
| `TELEGRAM_USER_ID` | Andrew's numeric Telegram ID: the only allowed user and the delivery chat |

Kubernetes refuses to start the Hermes container if a key is missing. Set or
replace keys from the repo root; each is prompted for without echo and encrypted
straight into the file, keeping the others:

```sh
python3 scripts/sops-set-secret.py --cluster-age-key \
  cluster/apps/hermes/api-keys.sops.yaml hermes hermes-agent-api-keys ANTHROPIC_API_KEY
```

`--cluster-age-key` decrypts with Flux's age identity from the current Kubernetes
context; without it, configure your age identity as in the root README or set
`SOPS_AGE_KEY_FILE`.

## OpenClaw data

OpenClaw's retained volumes and its `openclaw` and `openclaw-operator-system`
namespaces were deleted on 2026-11-11. Nothing from OpenClaw is left to migrate.

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
requests still use Hermes and Anthropic. It preserves the rest of the pipeline.

Verification sends one paid text request through the preferred Ada pipeline and
requires both a Hermes response and generated Piper audio. It does not exercise a
physical microphone, satellite wake word, speaker playback or device-control action.

To verify speech recognition too, run:

```sh
python3 scripts/verify-ha-voice.py --mcp
```

This synthesises “What is your name?”, streams the actual audio through Ada's
speech-to-text stage, checks the transcription, and downloads the generated reply
audio. `--mcp` adds a read-only query about the office lights and requires a retained
successful Home Assistant live-context tool result. This runs two paid model
requests and does not change device state. A physical satellite test is still
needed for its microphone, wake word and speaker.

Satellite1 ce2dc4 currently has **Hey Jarvis** and **Okay Nabu** wake-word models,
with Hey Jarvis selected. Naming the Assist pipeline Ada does not install an Ada
wake-word model. The old `wakeword-models` source has empty Ada model payloads;
custom Ada wake words need real compatible models and a separate firmware setup.

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

The API has no route (Ingress or HTTPRoute). NetworkPolicy permits the Home Assistant controller (API) and Alertmanager (webhook) and
denies other incoming pod traffic. Use a localhost port-forward for laptop access.
Telegram is the only messaging channel; the dashboard is not configured.
The pod has no Kubernetes service-account token, host mounts or container socket.
Egress permits cluster DNS, Home Assistant on port 8123, the Sproozi task service on 8443, and public IPv4 HTTPS,
excluding other private and link-local networks. This allows Anthropic, Telegram and upstream runtime downloads; it is not a
hostname allowlist. Agent Sandbox manages pod and volume lifecycle.
This cluster uses its normal container runtime, with no gVisor/Kata RuntimeClass.
The upstream image bootstraps as root and drops Hermes services to UID 10000.

## Sproozi runs

Hermes starts Sproozi's `triage` and `fix` runs through the `sproozi-tasks` MCP
server; see `../sproozi/README.md` for what each run may do. Hermes holds only the
task service's bearer token (`SPROOZI_TASK_TOKEN`); the model and GitHub
credentials stay in Sproozi's gateway. The init container builds
`/etc/hermes-ca/ca-bundle.pem` from the image's public roots plus
`sproozi-tasks-ca.crt`, and `SSL_CERT_FILE` points every client at it.
The `api_server` platform (Ada voice) still sees only the Home Assistant tools.

Check the connection after a pod restart:

```sh
kubectl -n hermes exec hermes -c hermes -- hermes mcp test sproozi-tasks
```

## Alert triage

Alertmanager sends warning and critical alerts (house device alerts excepted) to
the `alertmanager` webhook route on port 8644, with the shared token in an
`X-Gitlab-Token` header. Hermes then:

1. runs `sre/sre_alerts.py` on the payload. It keeps only alerts Andrew has not
   decided about and records them as pending in `/opt/data/sre/decisions.json`.
   An alert is keyed by alert name, namespace and the object it names, such as
   `KubePodCrashLooping/games/bedrock`;
2. follows the `sre-alerts` skill (`sre/SKILL.md`): submits a Sproozi `triage` run
   per alert, waits, and sends one Telegram message per alert, ending with
   *fix · ignore · later*;
3. on Andrew's Telegram reply, records the decision with
   `sre_alerts.py decide KEY ignore|later|fix` and, for *fix*, submits Sproozi's
   `fix` run, which opens a home-ops PR.

| Decision | Effect |
| --- | --- |
| *ignore* | Never asked again, even after the alert resolves; `decide KEY clear` undoes it |
| *later* | Asked again after N hours (default 24) if still firing; the route's hourly repeat delivers it |
| *fix* | Not asked again while the fix runs; a recurrence after the alert resolves is asked as new |
| no answer | Asked again after 24 hours if still firing |

The webhook platform's tools are web/vision and `sproozi-tasks` only: no Home
Assistant, terminal or files for untrusted alert text. Telegram answers only
`TELEGRAM_USER_ID` and is the full assistant. The init container copies the script
and skill from the `hermes-sre` ConfigMap on every start. Flux substitution is
disabled for that ConfigMap. `tests/test_sre_alerts.py` covers the decision rules.

Inspect or change decisions:

```sh
kubectl -n hermes exec hermes -c hermes -- python3 /opt/data/scripts/sre_alerts.py list
kubectl -n hermes exec hermes -c hermes -- python3 /opt/data/scripts/sre_alerts.py decide 'KEY' clear
```
