# Sproozi

[Sproozi](https://github.com/andrewmccall/sproozi) runs coding agents in disposable
sandbox Pods and gives them access to outside services only through its gateway.
Hermes (`../hermes`) is the persistent assistant that asks it for runs.

Sproozi is an early preview. Its gateway can read Pods, Pod logs, events,
ServiceAccounts, Services and workload controllers in **every** namespace. It can
read Secrets in no namespace. A run sees only what its AgentPolicy grants. Installing it on vecna accepts that read
access (decided 2026-11-10).

## What is here

| File | Source |
| --- | --- |
| `install.yaml` | `install/install.yaml` from the v0.2.6 Kubernetes release archive, unchanged |
| `certificates.yaml` | `self-managed-ca/certificates.yaml` from the same archive, unchanged |
| `../../crds/sproozi/crds.yaml` | `crds.yaml` from the same archive, unchanged |
| `kustomization.yaml` | Patches for this cluster, described below |
| `executor-claude.*`, `executor-codex.*` | Two remote executors, adapted from the release's examples ([Remote executors](#remote-executors)) |

The release creates the `sproozi-system` and `sproozi-agents` namespaces, the
controller, the shared gateway and a small certificate controller. That controller
creates the gateway's private CA, its TLS certificate and the
`sproozi-sandbox-trust` ConfigMap in `sproozi-agents`. Its Secrets are empty in
Git; the certificate controller fills them. Deleting this app deletes the CA.

Patches:

- The certificate's DNS name uses `cluster.andrewmccall.com`; the release names
  `cluster.local`, which this cluster does not use.
- `SPROOZI_ENABLED_CAPABILITIES` is `kubernetes.read,model.inference,github.pull_request`
  (the release also enables package installs and egress, which nothing here uses).
  The gateway refuses to start a capability without its credential. Model calls
  use the runs' own Claude sign-in (Claude subscription, below); pull requests use
  `capability-proxy-github-app.sops.yaml` (`app-id`, `installation-id`,
  `private-key.pem` of the `drew-pull-request-agent` App, installed only on home-ops),
  set with `scripts/sops-set-secret.py`.
- The certificate also names `platform.claude.com`, where the gateway forwards
  Claude Code's sign-in and token refresh in workload mode.

Each patch tests the release's original value first, so a new release that changes
it fails to render instead of being silently overwritten.

## SRE workflows for Hermes

Hermes starts runs through the **task service** (`tasks.yaml`), an MCP server at
`https://sproozi-tasks.sproozi-system.svc:8443/mcp`. `tasks.json` maps each workflow
name to a fixed template and capabilities; Hermes supplies only the task text, so
it cannot choose an image, model, policy or credential.

| Workflow | Template / runtime | Model | Can do |
| --- | --- | --- | --- |
| `triage` | `sre-triage` / `claude-haiku` | `claude-haiku-5-5` | Read pods, logs, events, services, Deployments, ReplicaSets, StatefulSets; 15 min; 2 at once |
| `fix` | `sre-fix` / `claude-sonnet` | `claude-sonnet-5-5` | The same reads, plus one PR against `andrewmccall/home-ops` `main`; 45 min; 1 at once |

Both are in `sre.yaml`. Runs use the release's `sproozi-native` image (Claude Code,
git, gh, kubectl). Each runtime sets the gateway proxy and git identity, then runs
Sproozi's `claude-launch.py` from the run contract (Sproozi ADR 0054): one
`claude --print`, whose final answer becomes the run result (cut to 3,584 bytes and
marked truncated if longer); a Claude error fails the run with no result. A run
holds only its own Claude login; the gateway adds the GitHub App token to requests
it allows. Budgets cap tokens only; the Claude plan's usage limits are the ceiling.

Policy gaps to know when reading a triage: Sproozi's Kubernetes read covers only
the resources above, so triage cannot see Secrets, ConfigMaps, nodes, DaemonSets,
PVCs or Flux objects. Its namespace list has no wildcard; **add new namespaces to
both policies in `sre.yaml` and to the executor policies in `executor-*.yaml`** (at most 32).

### Claude subscription

The runs use Claude Code's own sign-in to Andrew's Claude plan, not an API key:
the gateway runs in workload mode (`model-gateway-auth`, generated in
`kustomization.yaml`) and holds no Anthropic key or token, so it forwards the
run's own credential and still inspects and counts every call. Runs count
against the plan's usage limits. Hermes is unaffected: it has its own API key and
does not use this gateway.

The login lives in the claim `sproozi-login-claude-code-default` in
`sproozi-agents` (Longhorn), which Sproozi creates and never deletes. Every
runtime here mounts it; `claude-launch.py` copies `.credentials.json` into the
run's fresh home and writes refreshes back, so a refreshed token reaches the next
run. A run can read its own login.

Sign in, or sign in again after the login expires or is revoked:

```sh
run=$(kubectl create -o jsonpath='{.metadata.name}' -f - <<'RUN'
apiVersion: sproozi.com/v1alpha1
kind: AgentRun
metadata:
  generateName: claude-login-
  namespace: sproozi-system
spec:
  templateRef: {name: claude-login}
  capabilities: [model.inference]
  task: Wait for an operator sign-in.
RUN
)
kubectl wait -n sproozi-agents pod -l sproozi.com/agentrun=$run --for=condition=Ready --timeout=180s
pod=$(kubectl get pods -n sproozi-agents -l sproozi.com/agentrun=$run -o name)
kubectl exec -it -n sproozi-agents "$pod" -c agent -- python3 /etc/sproozi/contract/claude-launch.py --login
```

In Claude Code run `/login`, choose the Claude account, open the link on your own
machine, paste the code back, then `/exit`. Delete the AgentRun afterwards
(`kubectl delete agentrun -n sproozi-system $run`); it ends by itself after 30
minutes. `claude-login.yaml` holds its runtime, policy (model calls only) and
template.

The task service's TLS certificate is signed by a private CA made for it whose
key was discarded; Hermes trusts `../hermes/sproozi-tasks-ca.crt`. The certificate
expires on 2029-11-09. To replace it, make a new CA and certificate for
`sproozi-tasks.sproozi-system.svc`, store the certificate and key with
`scripts/sops-set-secret.py` in `task-tls.sops.yaml` (`tls.crt`, `tls.key`), and
replace the CA file. The bearer token is in `task-token.sops.yaml` and, as
`SPROOZI_TASK_TOKEN`, in Hermes's Secret; rotate both together.

## Remote executors

Two remote executors run Andrew's own interactive sessions on vecna, so a
session can keep running here, or start here, while his machine is away. An
executor serves one harness, so there is one per namespace:

| Namespace | Placement | Harness | Model | Starts sessions by |
| --- | --- | --- | --- | --- |
| `sproozi-claude` | `vecna-claude` | Claude Code | `claude-opus-5-5` | `sproozi move --remote` only |
| `sproozi-codex` | `vecna-codex` | Codex | Codex's default | `sproozi run --remote` or `sproozi move --remote` |

Each namespace holds the executor (`session-profile` from the `sproozi-native`
image), its RBAC, state claim, labelled Service and the CLI's `sproozi-cli`
identity, plus the AgentRuntime, AgentPolicy and AgentTemplate its runs use. The
sandboxes themselves run in `sproozi-agents`, like every other run.

- **Configuration.** `executor-<harness>.json` is the executor's configuration,
  made into an immutable ConfigMap whose name carries a hash; changing it
  restarts the executor. `instructionDigest` is the SHA-256 of the template's
  `instructions`, which must be byte-identical to `local.instructions` in the
  local `~/.sproozi/config.json`; change all three together.
  `maxCheckpointBytes` (32 MiB) must equal the local `local.maxCheckpointBytes`.
- **Deadline.** v0.2.6 caps `maxExecutionDuration` at one hour, so the policies
  and executors allow at most one hour from a session's start. The local
  service gives a session 30 minutes (`maxDuration`); a move never extends it.
  Upstream is removing the cap (deadlines become optional for work a person
  starts); raise or remove both settings after upgrading.
- **Allowances.** A moved session keeps its own allowance from the local
  `config.json` (`model.inference`, 200,000 tokens now), which must be bounded
  and fit the executor's ceiling (10,000,000) and policy budget. A `run
  --remote` task gets every allowance in `executor-codex.json`.
- **Access.** Policies allow model calls, pull requests to `andrewmccall/home-ops`
  and `andrewmccall/sproozi` (base `main`), and the same Kubernetes reads as
  the SRE runs. Pull requests and Git fetches use the GitHub App, which is
  installed only on home-ops: install it on `sproozi` too before using that
  repository.
- **Logins.** Claude Code sessions use the same login claim as the SRE runs,
  `sproozi-login-claude-code-default`, so they start signed in. Every runtime
  that mounts it (the SRE runs, `claude-login.yaml` and the sessions) runs as
  UID/GID 1000, the native image's own user: Kubernetes applies each Pod's
  `fsGroup` to the claim when it mounts, so a different group would take the
  login from the others. Keep them equal. Codex uses its own claim,
  `sproozi-login-codex-default`, created on first use.
- **TLS.** Each executor's certificate (`executor-<harness>-credentials.sops.yaml`,
  `tls.crt` and `tls.key`, for `sproozi-executor.<namespace>.svc`) is signed by
  a private CA made for it, whose key was discarded; `executor-<harness>-ca.crt`
  is published as the immutable `sproozi-remote-executor` ConfigMap that the CLI
  trusts. Both expire on 2029-11-12. To replace them, make a new CA and
  certificate, store them with `scripts/sops-set-secret.py`, replace the CA
  file and restart the executor. Codex's Secret also holds `work-token`, which
  the executor requires with `repositories`; nothing uses it yet (it would let
  Hermes submit work).
- **State.** Journals and checkpoints are on `longhorn`, so they are in the
  nightly off-site backup. Sproozi never deletes registrations or stored
  profiles (ConfigMaps in the executor's namespace).

### CLI and contexts

The CLI and local service must match the cluster's version, v0.2.6: upgrade
them, then run `sproozi service stop` and `sproozi service start`. The
kubeconfig's cluster entry must reach vecna's API server from where you are.

With an administrator context, write one context per executor:

```sh
CLUSTER=$(kubectl config view --minify -o jsonpath='{.clusters[0].name}')
for h in claude codex; do
  NS=sproozi-$h
  kubectl -n "$NS" wait --for=jsonpath='{.data.token}' secret/sproozi-cli-token
  TOKEN=$(kubectl -n "$NS" get secret sproozi-cli-token -o jsonpath='{.data.token}' | base64 -d)
  kubectl config set-credentials "sproozi-cli-$h" --token="$TOKEN"
  kubectl config set-context "sproozi-$h" --cluster="$CLUSTER" --user="sproozi-cli-$h" --namespace="$NS"
  kubectl --context "sproozi-$h" auth can-i create pods --subresource=portforward   # yes
done
```

The token reaches only the executor in its namespace (`sproozi-cli` may
port-forward there and act as that one placement). To rotate it, delete the
`sproozi-cli-token` Secret, let Flux recreate it and run the loop again.
`sproozi sessions --remote --context sproozi-claude` checks the connection.

### Sessions

Claude Code sessions start on this machine and move to vecna. `run --remote`
submits only Codex tasks in v0.2.6; starting Claude Code sessions remotely is
being worked on upstream.

```sh
sproozi run                                   # in the repository; note the session ID
sproozi move ID --remote --context sproozi-claude
sproozi attach ID                             # Ctrl-] detaches
sproozi move ID --local                       # bring it back
```

A Codex task starts on vecna from an approved repository (`home-ops` or
`sproozi`, at `main`):

```sh
sproozi run --remote --context sproozi-codex --repository home-ops --task 'Fix ...'
sproozi sessions --remote --context sproozi-codex
sproozi status ID --remote --context sproozi-codex
sproozi pull ID --context sproozi-codex       # take it over on this machine
```

The local service owns moved sessions, so it must be running to move, attach
or stop them; the session itself runs to its deadline either way.

**First sign-in.** Claude Code: the SRE login is already in the claim; if a
session asks, type `/login` in the attached session and finish the browser step
on your own machine. Codex: its login is empty until you sign in once inside a
session on vecna. `sproozi attach` reaches only sessions this machine's service
owns, not a `run --remote` task, and Codex waits at its sign-in screen without a
login, so sign in through a moved session: add
Codex locally (`sproozi init --harness codex --sign-in`), start a Codex session,
`sproozi move ID --remote --context sproozi-codex`, `sproozi attach ID`, choose
ChatGPT sign-in with a device code and open the page on your own machine. Later
Codex sessions and tasks on vecna use that login.

## Upgrading

Download the new release's Kubernetes archive and `checksums.txt`, check the
archive, and replace the three vendored files. Update the `sproozi-native`
image digest in `sre.yaml`, `claude-login.yaml` and `executor-*.yaml` too. Read the release notes'
"Breaking changes" first. Before crossing a minor version, delete finished
AgentRuns and stop running ones while the old controller still runs.

```sh
VERSION=0.2.6
curl -fsSLO "https://github.com/andrewmccall/sproozi/releases/download/v$VERSION/sproozi_${VERSION}_kubernetes.tar.gz"
curl -fsSLO "https://github.com/andrewmccall/sproozi/releases/download/v$VERSION/checksums.txt"
grep "sproozi_${VERSION}_kubernetes.tar.gz" checksums.txt | shasum -a 256 -c -
```

## First check

The release's first check needs no model or GitHub credential. It starts a sandbox
that lists Sproozi's Pods through the gateway, then tries three things its
policy forbids. Run it from the extracted archive; its resources are not kept in Git:

```sh
kubectl apply -f sproozi-release/first-check/resources.yaml
kubectl create -f sproozi-release/first-check/agentrun.yaml
kubectl logs -n sproozi-agents -l sproozi.com/agentrun=first-check -c agent -f
kubectl wait agentrun/first-check -n sproozi-system --for=jsonpath='{.status.phase}'=Succeeded --timeout=300s
kubectl delete agentrun first-check -n sproozi-system
kubectl delete -f sproozi-release/first-check/resources.yaml
```

The log must show `PERMITTED: Pod read succeeded` and three `DENIED` lines.
`UNEXPECTED: ... reachable` means network policy is not enforced from Pod start.
