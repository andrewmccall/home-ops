# Cloudflare tunnel

One tunnel, `public`, is the only way in from the internet: the router has no port
forwards. `cloudflared-public` (two connectors, so a restart drops nothing) sends every
request to the Envoy Gateway `external`, which picks the backend by host and path. The
tunnel knows no hostnames, so nothing here changes when a service goes public: see
[Making a service public](../README.md#making-a-service-public).

- **Locally managed.** Its rules are the ConfigMap in `public.yaml`, not settings in the
  Cloudflare dashboard; the token only authenticates the connectors. After editing the
  rules, `kubectl -n networking rollout restart deploy/cloudflared-public`.
- **TLS** to Envoy is verified against each request's host (`matchSNItoHost`), which the
  `*.andrewmccall.com` certificate on the Gateway covers.
- **DNS.** `external-dns-cloudflare` (`../external-dns/`) creates each public host's
  proxied CNAME to `<PUBLIC_TUNNEL_ID>.cfargotunnel.com` (`cluster/base/config.yaml`).
- **Locked down.** The `cloudflared-public` NetworkPolicy lets the connectors reach only
  DNS, the external Gateway's Envoy pods and Cloudflare's edge (7844, 443).

## Check it

```sh
kubectl -n networking logs deploy/cloudflared-public | grep -c "Registered tunnel connection"
cloudflared tunnel info public          # needs `cloudflared tunnel login`
```

## Rotate the token or recreate the tunnel

```sh
cloudflared tunnel login                                  # once per machine
cloudflared tunnel token public | scripts/cloudflared-tunnel-secret.sh
```

Commit the re-encrypted `public-token.sops.yaml`, merge, then restart the Deployment.
To recreate the tunnel: `cloudflared tunnel create public`, set `PUBLIC_TUNNEL_ID` in
`cluster/base/config.yaml` to the new ID, write the token as above, and delete the old
tunnel's DNS records so external-dns recreates them for the new one.
