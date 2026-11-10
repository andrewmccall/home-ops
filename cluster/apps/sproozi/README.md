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
| `install.yaml` | `install/install.yaml` from the v0.2.4 Kubernetes release archive, unchanged |
| `certificates.yaml` | `self-managed-ca/certificates.yaml` from the same archive, unchanged |
| `../../crds/sproozi/crds.yaml` | `crds.yaml` from the same archive, unchanged |
| `kustomization.yaml` | Patches for this cluster, described below |

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
  The gateway refuses to start a capability without its credential:
  `model-gateway-credentials.sops.yaml` (`anthropic-api-key`) and
  `capability-proxy-github-app.sops.yaml` (`app-id`, `installation-id`,
  `private-key.pem` of the `drew-pull-request-agent` App, installed only on home-ops).
  Set them with `scripts/sops-set-secret.py`.

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
git, gh, kubectl). A run never holds a credential: the gateway adds the Anthropic
key and the GitHub App token to requests it allows. Budgets cap tokens only; set a
spending limit on the gateway's Anthropic workspace as the money ceiling.

Policy gaps to know when reading a triage: Sproozi's Kubernetes read covers only
the resources above, so triage cannot see Secrets, ConfigMaps, nodes, DaemonSets,
PVCs or Flux objects. Its namespace list has no wildcard; **add new namespaces to
both policies in `sre.yaml`** (at most 32).

The task service's TLS certificate is signed by a private CA made for it whose
key was discarded; Hermes trusts `../hermes/sproozi-tasks-ca.crt`. The certificate
expires on 2029-11-09. To replace it, make a new CA and certificate for
`sproozi-tasks.sproozi-system.svc`, store the certificate and key with
`scripts/sops-set-secret.py` in `task-tls.sops.yaml` (`tls.crt`, `tls.key`), and
replace the CA file. The bearer token is in `task-token.sops.yaml` and, as
`SPROOZI_TASK_TOKEN`, in Hermes's Secret; rotate both together.

## Upgrading

Download the new release's Kubernetes archive and `checksums.txt`, check the
archive, and replace the three vendored files. Read the release notes'
"Breaking changes" first. Before crossing a minor version, delete finished
AgentRuns and stop running ones while the old controller still runs.

```sh
VERSION=0.2.4
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
