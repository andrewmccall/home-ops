# OpenClaw Access Notes

## Ingress + reverse proxy notes

- In this cluster, OpenClaw is exposed with the `internal` ingress class at `openclaw-gateway.andrewmccall.com`.
- The internal ingress controller listens on HTTPS (`443`) only (`enableHttp: false`), so upstream proxies must target `https://10.44.0.20:443`.
- If you front this with another hostname (for example `https://internal.andrewmccall.com`), preserve the original `Host` header expected by the ingress rule (`openclaw-gateway.andrewmccall.com`) or add a matching ingress host.

## OpenClaw gateway auth/origins (operator docs)

From `openclaw-rocks/k8s-operator` README:

- Do not set `gateway.mode: local` in Kubernetes.
- For Control UI via ingress, include the token in the URL fragment:
  - `https://openclaw-gateway.andrewmccall.com/#token=<token>`
- Use `spec.gateway.controlUiOrigins` to add non-default reverse-proxy origins.
- The operator auto-injects `gateway.controlUi.allowedOrigins` from localhost + ingress hosts + `spec.gateway.controlUiOrigins`.

This repo sets:

- `spec.gateway.controlUiOrigins: ["https://internal.andrewmccall.com", "https://openclaw-gateway.andrewmccall.com"]`
- `spec.config.mergeMode: merge`

## 504 timeout troubleshooting

If ingress returns `504 Gateway Time-out` for OpenClaw:

1. Check ingress class and host:
	- `kubectl -n openclaw get ingress openclaw-gateway -o yaml`
2. Check ingress-controller logs for upstream timeout:
	- `kubectl -n networking logs deploy/nginx-internal-controller --since=15m | grep openclaw-gateway`
3. Confirm NetworkPolicy allows traffic from `networking` namespace ingress controller pods to OpenClaw gateway ports.

This repo includes `gateway-allow-internal-nginx.yaml` to allow ingress-controller traffic to the OpenClaw pod on ports `18790` and `18794`.

## Port-forward for UI (Canvas)

```bash
kubectl port-forward -n openclaw svc/home-ops-openclaw 18789:18789
```

Open in browser:

- http://localhost:18789/__openclaw__/canvas/

## Optional: direct Canvas service port (not the main UI route)

```bash
kubectl port-forward -n openclaw svc/home-ops-openclaw 18793:18793
```

If needed, test reachability:

```bash
curl -I http://localhost:18793
```

## Quick checks

```bash
kubectl get pod -n openclaw home-ops-openclaw-0
kubectl --namespace openclaw logs pod/home-ops-openclaw-0 -c openclaw --tail=30
```
