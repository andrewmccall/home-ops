#!/usr/bin/env bash
# Writes the public tunnel's token as the SOPS-encrypted Secret cloudflared-public in
# cluster/apps/networking/cloudflared/public-token.sops.yaml. The token is read from
# stdin so it stays out of shell history, and goes straight to sops through a pipe: it
# is never printed, written to disk in plaintext or passed as an argument. Encrypting
# needs only the age recipient in .sops.yaml.
#
#   cloudflared tunnel token public | scripts/cloudflared-tunnel-secret.sh
#
# Then commit the file and merge; the Deployment needs a restart to pick it up:
#   kubectl -n networking rollout restart deploy/cloudflared-public
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
rel="cluster/apps/networking/cloudflared/public-token.sops.yaml"
[ $# -eq 0 ] || { sed -n '2,12p' "$0" >&2; exit 2; }

token="$(cat | tr -d '[:space:]')"
[ -n "$token" ] || { echo "no token on stdin" >&2; exit 2; }
# A tunnel token is base64 JSON with account (a), tunnel id (t) and secret (s).
printf '%s' "$token" | base64 -d 2>/dev/null | jq -e 'has("a") and has("t") and has("s")' >/dev/null 2>&1 \
  || { echo "stdin is not a Cloudflare tunnel token" >&2; exit 2; }

cd "$root"
printf '%s' "$token" \
  | kubectl create secret generic cloudflared-public -n networking --from-file=token=/dev/stdin \
      --dry-run=client -o yaml \
  | sops -e --filename-override "$rel" --input-type yaml --output-type yaml /dev/stdin > "$rel.tmp"
mv "$rel.tmp" "$rel"
echo "wrote $rel (encrypted); commit it and merge"
