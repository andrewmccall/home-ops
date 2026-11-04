#!/usr/bin/env bash
# Create or update the GitHub push webhooks that call Flux's Receivers
# (cluster/core/flux-system/webhook/). Run after Flux has applied the Receivers:
# each Receiver's path, /hook/<sha256>, exists only in its .status.webhookPath.
#
#   scripts/flux-github-webhooks.sh [--token-file PATH]
#
# The shared secret comes from --token-file, or else is decrypted from the SOPS
# secret (needs the age key). It is never printed or passed on a command line.
# Safe to re-run: an existing hook pointing at the same host is updated in place,
# which is also how a rotated token reaches GitHub. Each hook is then pinged.
# Needs kubectl (cluster access), gh (repo admin), jq, and sops without --token-file.
set -euo pipefail

HOST="${FLUX_WEBHOOK_HOST:-gh-webhook.andrewmccall.com}"
NAMESPACE=flux-system
# repository -> Receiver name
HOOKS=("andrewmccall/home-ops=home-ops" "andrewmccall/survival=survival")

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SECRET_FILE="$ROOT/cluster/core/flux-system/webhook/github-webhook-token.sops.yaml"

token_file=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --token-file) token_file="$2"; shift 2 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

work="$(mktemp -d)"
chmod 700 "$work"
trap 'rm -rf "$work"' EXIT

if [[ -z "$token_file" ]]; then
  token_file="$work/token"
  (umask 077; sops -d "$SECRET_FILE" | yq -r '.stringData.token' > "$token_file")
fi
if [[ ! -s "$token_file" ]]; then
  echo "token file is empty or missing: $token_file" >&2
  exit 1
fi

for entry in "${HOOKS[@]}"; do
  repo="${entry%%=*}"
  receiver="${entry#*=}"
  path="$(kubectl -n "$NAMESPACE" get receiver "$receiver" -o jsonpath='{.status.webhookPath}')"
  if [[ "$path" != /hook/* ]]; then
    echo "$receiver: Receiver has no webhookPath yet (is it applied and Ready?)" >&2
    exit 1
  fi
  url="https://$HOST$path"

  # The secret is read by jq from a file and sent on stdin, never as an argument.
  jq -n --rawfile secret "$token_file" --arg url "$url" '{
      name: "web", active: true, events: ["push"],
      config: {url: $url, content_type: "json", insecure_ssl: "0",
               secret: ($secret | rtrimstr("\n"))}
    }' > "$work/body.json"

  id="$(gh api "repos/$repo/hooks" --paginate \
    --jq ".[] | select((.config.url // \"\") | startswith(\"https://$HOST/hook/\")) | .id" | head -n1)"
  if [[ -n "$id" ]]; then
    gh api "repos/$repo/hooks/$id" -X PATCH --input "$work/body.json" --silent
    echo "$repo: updated hook $id -> $url"
  else
    id="$(gh api "repos/$repo/hooks" -X POST --input "$work/body.json" --jq .id)"
    echo "$repo: created hook $id -> $url"
  fi

  last="$(gh api "repos/$repo/hooks/$id/deliveries?per_page=1" --jq '.[0].id // 0')"
  gh api "repos/$repo/hooks/$id/pings" -X POST --silent
  status=""
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    sleep 2
    status="$(gh api "repos/$repo/hooks/$id/deliveries?per_page=1" \
      --jq ".[0] | select(.id > $last and .event == \"ping\") | \"\\(.status_code) \\(.status)\"")"
    [[ -n "$status" ]] && break
  done
  echo "$repo: ping delivery: ${status:-not seen yet; check gh api repos/$repo/hooks/$id/deliveries}"
done
