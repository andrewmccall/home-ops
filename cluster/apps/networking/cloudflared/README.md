# Cloudflare tunnels

Two remotely managed tunnels publish hostnames without opening router ports. Each runs
`cloudflared tunnel run` with a token; its routes (public hostnames) are configured on
the tunnel in Cloudflare Zero Trust, not in git. The proxied DNS record is created by the
dashboard, not external-dns.

| Tunnel | Deployment | Carries | Routes to |
|---|---|---|---|
| `ashes` | `cloudflared-ashes` (2 replicas) | Game traffic only: `ashes.andrewmccall.com`, `ashes-dev.andrewmccall.com` | nginx-external (HTTPS) |
| `vecna-infra` | `cloudflared-infra` (1 replica) | Cluster control-plane endpoints: `flux-webhook.andrewmccall.com/hook/` | the endpoint's Service directly |

Keep them apart: a game hostname never goes on `vecna-infra`, and an infrastructure
endpoint never goes on `ashes`. Each tunnel can then be rotated, scaled or shut off on its
own, and a game routing change cannot expose a cluster endpoint.

`cloudflared-infra` is limited by the `cloudflared-infra` NetworkPolicy (`infra.yaml`): it
may reach DNS, Flux's `webhook-receiver` (notification-controller port 9292) and
Cloudflare's edge on 7844 (tunnel) and 443 (API), and accepts only metrics on 2000. A new
endpoint on this tunnel needs an egress rule there too. It requests 10m CPU and 64Mi
(about 30Mi in use), limited to 256Mi. One replica is enough: while it restarts, missed
webhooks are covered by Flux polling.

## Create the vecna-infra tunnel (one-time)

1. Zero Trust → **Networks → Tunnels → Create a tunnel** → **Cloudflared**, name it
   `vecna-infra`, save. Copy the token from the install command (the value after
   `--token`); skip the connector install.
2. Store it (on the branch, or a follow-up PR) and merge:
   ```sh
   pbpaste | scripts/cloudflared-tunnel-secret.sh infra
   git add cluster/apps/networking/cloudflared/infra-token.sops.yaml
   ```
   The committed file holds a placeholder until then, and `cloudflared-infra` crash-loops
   on it. After Flux applies the real token:
   `kubectl -n networking rollout restart deploy/cloudflared-infra`.
3. **Public hostnames → Add a public hostname**:

   | Field | Value |
   |---|---|
   | Subdomain / Domain | `flux-webhook` / `andrewmccall.com` (the zone the game uses) |
   | Path | `^/hook/` |
   | Service | `HTTP` `webhook-receiver.flux-system.svc.cluster.andrewmccall.com:80` |

   The cluster DNS domain is `cluster.andrewmccall.com`; `.svc.cluster.local` does not
   resolve here.
4. Add no other routes. Requests that match no route get the tunnel's 404.

Check: the tunnel shows **Healthy** in the dashboard, and
`kubectl -n networking logs deploy/cloudflared-infra | grep -i "registered tunnel connection"`.

To rotate a token, refresh it in the tunnel's settings in Zero Trust, then repeat step 2.
