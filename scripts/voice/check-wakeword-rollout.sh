#!/usr/bin/env bash

set -euo pipefail

NAMESPACE="${NAMESPACE:-house}"
DEPLOYMENT_NAME="${DEPLOYMENT_NAME:-wyoming-openwakeword}"
HOUSE_KUSTOMIZATION="${HOUSE_KUSTOMIZATION:-house}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOUSE_DIR="${ROOT_DIR}/cluster/apps/house"

snapshot_generation() {
  local namespace="$1"
  local resource="$2"
  kubectl -n "${namespace}" get "${resource}" -o jsonpath='{.metadata.generation}' 2>/dev/null || echo "missing"
}

before_wakeword="$(snapshot_generation "${NAMESPACE}" "deployment/${DEPLOYMENT_NAME}")"
before_home_assistant="$(snapshot_generation "${NAMESPACE}" "deployment/home-assistant")"
before_voice="$(kubectl -n "${NAMESPACE}" get deployments -o json | python3 -c '
import json, sys
items = json.load(sys.stdin).get("items", [])
match = [item for item in items if item.get("metadata", {}).get("name", "").startswith("voice")]
print(match[0]["metadata"]["generation"] if match else "missing")
')"

if kubectl -n flux-system get kustomization "${HOUSE_KUSTOMIZATION}" >/dev/null 2>&1; then
  flux reconcile kustomization "${HOUSE_KUSTOMIZATION}" --with-source
else
  kubectl apply -k "${HOUSE_DIR}"
fi

kubectl -n "${NAMESPACE}" rollout status "deployment/${DEPLOYMENT_NAME}" --timeout=180s >/dev/null

after_wakeword="$(snapshot_generation "${NAMESPACE}" "deployment/${DEPLOYMENT_NAME}")"
after_home_assistant="$(snapshot_generation "${NAMESPACE}" "deployment/home-assistant")"
after_voice="$(kubectl -n "${NAMESPACE}" get deployments -o json | python3 -c '
import json, sys
items = json.load(sys.stdin).get("items", [])
match = [item for item in items if item.get("metadata", {}).get("name", "").startswith("voice")]
print(match[0]["metadata"]["generation"] if match else "missing")
')"

if [[ "${before_wakeword}" == "${after_wakeword}" ]]; then
  echo "ERROR: Wake-word deployment generation did not change" >&2
  exit 1
fi

if [[ "${before_home_assistant}" != "${after_home_assistant}" ]]; then
  echo "ERROR: Home Assistant deployment generation changed unexpectedly" >&2
  exit 1
fi

if [[ "${before_voice}" != "${after_voice}" ]]; then
  echo "ERROR: Voice deployment generation changed unexpectedly" >&2
  exit 1
fi

echo "Model-only rollout check passed."
