# Flux GitHub webhooks

A push to `main` on **andrewmccall/home-ops** or **andrewmccall/survival** triggers a Flux
reconcile within seconds, instead of on the next poll. Survival's CI `[skip ci]` image-tag
commits are ordinary pushes, so deploys trigger the same way. Polling stays on as the
fallback: if a delivery is lost, the next interval picks the change up.

## How it works

```
GitHub push -> https://flux-webhook.andrewmccall.com/hook/<sha256>
  -> Cloudflare tunnel "vecna-infra" (Deployment cloudflared-infra, networking)
     routes only ^/hook/ on this hostname; anything else gets the tunnel's 404
  -> Service webhook-receiver:80 (notification-controller, port 9292)
  -> Receiver home-ops or survival
  -> annotates GitRepository flux-system or survival with "reconcile now"
  -> source-controller fetches; kustomize-controller applies every Kustomization on that source
```

- **Receivers** (`receiver.yaml`): `home-ops` targets the `flux-system` GitRepository;
  `survival` targets `survival` (`cluster/apps/ashes/`), which feeds `ashes-map`, `ashes-dev`,
  `ashes-prod` and `ashes-ci`. Kustomizations are not listed: a new source artifact already
  reconciles them, and annotating them directly could apply the old artifact first.
- **One token, two Receivers.** Both read `github-webhook-token`. Separate Receivers mean a
  push reconciles only its own repo and each has its own path; one token means one secret
  to rotate.
- **Path.** Flux sets each Receiver's path to `/hook/` + sha256(token + name + namespace) and
  publishes it in `.status.webhookPath`. Rotating the token changes both paths.
- **Authentication.** GitHub signs every delivery with the token (HMAC-SHA256,
  `X-Hub-Signature-256`); the Receiver rejects unsigned or wrongly signed requests and
  events other than `push` and `ping`. A valid request can only ask Flux to fetch now.
- **Exposure.** The webhook-receiver port serves only Receiver hooks; Flux's event API is
  the separate `notification-controller` Service and is not routed. The hostname rides the
  infrastructure tunnel, not the game's (`cluster/apps/networking/cloudflared/`), and that
  tunnel's pods may reach only this Service, DNS and Cloudflare. No Ingress or DNS record
  is managed in git: the tunnel's public hostname owns the proxied Cloudflare record.

## Cloudflare tunnel hostname (one-time, dashboard)

Needs the `vecna-infra` tunnel (`cluster/apps/networking/cloudflared/README.md`). Its routes
live in Cloudflare Zero Trust, not in git. Under **Networks → Tunnels → vecna-infra →
Public hostnames → Add a public hostname**:

| Field | Value |
|---|---|
| Subdomain / Domain | `flux-webhook` / `andrewmccall.com` |
| Path | `^/hook/` |
| Service | `HTTP` `webhook-receiver.flux-system.svc.cluster.andrewmccall.com:80` |

Add no other routes. The cluster DNS domain is `cluster.andrewmccall.com`, so a
`.svc.cluster.local` address does not resolve here.

Optional: Cloudflare WAF custom rule on the zone to block anything not from GitHub:
`(http.host eq "flux-webhook.andrewmccall.com" and not ip.src in {<gh api meta --jq '.hooks[]'>})`
→ Block. GitHub occasionally adds ranges; a stale list drops deliveries until polling
catches up, so re-check it when deliveries fail with 403.

## Create or update the GitHub webhooks

After Flux has applied the Receivers (and the tunnel hostname exists):

```sh
kubectl -n flux-system get receiver   # both Ready, with a webhook path
scripts/flux-github-webhooks.sh [--token-file PATH]
```

The script reads each Receiver's `.status.webhookPath`, creates the `push` webhook on its
repo (or updates the existing one for this host), pings it and prints the delivery status.
Without `--token-file` it decrypts the token from the SOPS secret. It never prints the
token and is safe to re-run.

## Verify

```sh
# Ping: expect "200 OK" from the script, or check the latest delivery
gh api repos/andrewmccall/survival/hooks --jq '.[] | select((.config.url // "") | contains("flux-webhook")) | .id'
gh api repos/andrewmccall/survival/hooks/<id>/deliveries --jq '.[0:3][] | [.event, .status_code, .delivered_at] | @tsv'

# Push: the Receiver logs the request and the GitRepository fetches within seconds
kubectl -n flux-system logs deploy/notification-controller --since=5m | grep -i receiver
kubectl -n flux-system get gitrepository survival flux-system -o wide
flux get kustomizations
```

## Polling intervals

With the webhooks working, polling is only the safety net. GitHub does not redeliver a
failed webhook on its own, so a delivery lost to a tunnel restart or a cluster outage
waits for the next poll.

| Object | Interval | Why |
|---|---|---|
| GitRepository `flux-system` (home-ops) | 30m | Fallback for a missed delivery. Set by a patch in `cluster/flux-system/flux-system/kustomization.yaml`, since `flux bootstrap` generates 1m. |
| GitRepository `survival` | 30m | Same; prod follows survival's `main`, so 30m (not 1h) bounds a missed deploy. |
| Kustomizations | unchanged (3m to 10m) | The interval is also drift correction: how soon a hand edit or a deleted object is put back. It never fetches Git; a new artifact reconciles them at once. |
| HelmRepositories | 1h; `home-ops` 10m | Not covered by webhooks. A Renovate bump in git arrives by webhook, but the chart is resolved from the cached index, so a chart published within the last hour can take up to an hour to resolve. `home-ops` charts are published and consumed here, so it stays at 10m. |
| GitRepositories for third-party CRDs | 30m | Pinned to tags or upstream branches; not covered by webhooks. |

Force a fetch any time with `flux reconcile source git flux-system` (or `survival`).

## Rotate the token

```sh
umask 077
openssl rand -hex 32 | tr -d '\n' > /tmp/flux-webhook-token
{ printf 'apiVersion: v1\nkind: Secret\nmetadata:\n  name: github-webhook-token\n  namespace: flux-system\ntype: Opaque\nstringData:\n  token: "'
  cat /tmp/flux-webhook-token; printf '"\n'; } \
  | sops -e --filename-override cluster/core/flux-system/webhook/github-webhook-token.sops.yaml \
      --input-type yaml --output-type yaml /dev/stdin \
  > cluster/core/flux-system/webhook/github-webhook-token.sops.yaml
```

Merge it, wait for Flux to apply it (the Receivers' `webhookPath` changes), then re-run
`scripts/flux-github-webhooks.sh --token-file /tmp/flux-webhook-token` and delete the file.
Deliveries fail between the merge and the re-run; polling covers the gap.
