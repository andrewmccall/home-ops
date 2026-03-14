# OpenClaw Access Notes

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
