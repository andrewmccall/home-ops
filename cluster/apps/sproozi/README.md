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
- `SPROOZI_ENABLED_CAPABILITIES` is `kubernetes.read` until the model and GitHub
  App credentials exist. The gateway refuses to start a capability without them.

Each patch tests the release's original value first, so a new release that changes
it fails to render instead of being silently overwritten.

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
