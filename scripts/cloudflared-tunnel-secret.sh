#!/usr/bin/env bash
# Writes a Cloudflare tunnel token as the SOPS-encrypted Secret cloudflared-<tunnel>
# in cluster/apps/networking/cloudflared/<tunnel>-token.sops.yaml. The token is read
# from stdin so it stays out of shell history, and goes straight to sops through a
# pipe: it is never printed, written to disk in plaintext or passed as an argument.
# Encrypting needs only the age recipient in .sops.yaml.
#
#   pbpaste | scripts/cloudflared-tunnel-secret.sh infra    # tunnel vecna-infra
#   pbpaste | scripts/cloudflared-tunnel-secret.sh ashes    # tunnel ashes
#
# Copy the token from Zero Trust -> Networks -> Tunnels -> <tunnel> -> Configure
# (the value after "--token" in the install command). Then commit the file and
# merge; Flux applies it and the Deployment needs a restart to pick it up:
#   kubectl -n networking rollout restart deploy/cloudflared-<tunnel>
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
usage() { sed -n '2,14p' "$0" >&2; exit 2; }

[ $# -eq 1 ] || usage
case "$1" in
  ashes|infra) tunnel="$1" ;;
  *) usage ;;
esac
rel="cluster/apps/networking/cloudflared/$tunnel-token.sops.yaml"

token="$(cat | tr -d '[:space:]')"
[ -n "$token" ] || { echo "no token on stdin" >&2; exit 2; }
# A tunnel token is base64 JSON with account (a), tunnel id (t) and secret (s).
printf '%s' "$token" | base64 -d 2>/dev/null | jq -e 'has("a") and has("t") and has("s")' >/dev/null 2>&1 \
  || { echo "stdin is not a Cloudflare tunnel token" >&2; exit 2; }

cd "$root"
printf '%s' "$token" \
  | kubectl create secret generic "cloudflared-$tunnel" -n networking --from-file=token=/dev/stdin \
      --dry-run=client -o yaml \
  | sops -e --filename-override "$rel" --input-type yaml --output-type yaml /dev/stdin > "$rel.tmp"
mv "$rel.tmp" "$rel"
echo "wrote $rel (encrypted); commit it and merge"
