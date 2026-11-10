# Authentik: one login for the cluster's apps

Authentik at `https://auth.${DOMAIN}` (LAN only, internal Gateway) holds the users. Apps
log in against it with OIDC and create the user on first login; Authentik groups decide
who may use an app and with what role. It works with the internet down: the hostname is
on the home gateway's DNS (external-dns-unifi), the database is local, and nothing in a
login leaves the house.

| Piece | Where |
|---|---|
| Server and worker | `helmrelease.yaml` (Docker Hub `authentik/server`) |
| Database | `database.yaml`, a CloudNativePG `Cluster`; the operator makes `authentik-db-app` |
| Groups, applications, who may use them | `blueprints.yaml`, applied by the worker |
| Users, passwords, MFA | Authentik itself, not git (this repo is public) |
| Secret key, akadmin bootstrap, client secrets | `secrets.sops.yaml` |

## Groups

| Group | Gets |
|---|---|
| `admins` | Authentik superuser, Grafana server admin, the Longhorn UI, the code-servers |
| `household` | Grafana Viewer |

A user in neither group cannot open any app. Add a person in the Authentik admin UI
(Directory > Users), then add them to a group.

## Apps using it

| App | How | Client secret also in |
|---|---|---|
| Grafana | Its own OIDC login (`auth.generic_oauth` in `monitoring/grafana/helmrelease.yaml`); role from the `groups` claim on every login. The local `admin` login stays as the way in when Authentik is down. | `monitoring/grafana/oidc.sops.yaml` |
| Longhorn UI | No login of its own: an Envoy `SecurityPolicy` (`core/longhorn/securitypolicy.yaml`) logs in before the route. | `core/longhorn/oidc.sops.yaml` |
| Home Assistant and ESPHome code-servers | The same, one client for both hosts (`house/code-servers-securitypolicy.yaml`); admins only. | `house/code-servers-oidc.sops.yaml` |

### Adding an app

1. Generate a client secret and add it to `secrets.sops.yaml` and to a Secret beside the
   app (`scripts/sops-set-secret.py`). Restart the Authentik worker afterwards: it reads
   the secrets as environment variables at start.
2. Add an `oauth2provider`, an `application` and a `policybinding` per allowed group to
   `blueprints.yaml`, copying an existing entry. The redirect URI must match exactly.
3. Point the app at the issuer `https://auth.${DOMAIN}/application/o/<slug>/`. An app with
   no login of its own gets a `SecurityPolicy` with `oidc` targeting its HTTPRoute
   (redirect `https://<host>/oauth2/callback`); Envoy then needs a secret with key
   `client-secret` in the route's namespace.
4. After the first deploy, restart the Authentik worker (step 1), then check the policy:
   `kubectl get securitypolicy -A`. If it reports "failed fetching openid-configuration
   ... 404", Envoy looked the application up before the blueprint created it and keeps
   that result: `kubectl -n networking rollout restart deploy/envoy-gateway`.

On a new install the blueprint can fail its first run, before Authentik's default flows
exist; the worker retries it. `kubectl -n authentik exec deploy/authentik-worker -- ak
apply_blueprint mounted/cm-authentik-blueprints/blueprints.yaml` applies it at once.
Blueprints are applied, not owned: removing an entry leaves the object in Authentik, so
delete it in the UI too.

## The akadmin account

The bootstrap admin `akadmin` exists from the first start; its password is in
`secrets.sops.yaml`:

```bash
kubectl -n authentik get secret authentik-secrets -o jsonpath='{.data.AUTHENTIK_BOOTSTRAP_PASSWORD}' | base64 -d | pbcopy
```

Use it to create your own user in `admins`, then deactivate `akadmin`. The bootstrap
values apply only to an empty database; changing them later does nothing.

## If Authentik is down

Grafana still takes its local `admin` login. The Longhorn UI returns an error until
Authentik is back; `kubectl -n longhorn port-forward svc/longhorn-frontend 8080:80`
reaches it directly. Never change `AUTHENTIK_SECRET_KEY`: it signs sessions and user IDs.
