#!/usr/bin/env bash

set -euo pipefail

NAMESPACE="${NAMESPACE:-house}"
CONFIGMAP_NAME="${CONFIGMAP_NAME:-wakeword-models}"
SERVICE_NAME="${SERVICE_NAME:-wyoming-openwakeword}"
DEPLOYMENT_NAME="${DEPLOYMENT_NAME:-wyoming-openwakeword}"
PORT="${PORT:-10400}"

echo "Checking ConfigMap ${CONFIGMAP_NAME} in namespace ${NAMESPACE}..."
kubectl -n "${NAMESPACE}" get configmap "${CONFIGMAP_NAME}" >/dev/null
kubectl -n "${NAMESPACE}" get configmap "${CONFIGMAP_NAME}" -o json | python3 -c '
import json, sys
data = json.load(sys.stdin)
binary = data.get("binaryData", {})
missing = [key for key in ("ada.tflite", "hey_ada.tflite") if key not in binary]
if missing:
    raise SystemExit(f"Missing ConfigMap binaryData keys: {missing}")
'

echo "Checking Service ${SERVICE_NAME} port ${PORT}..."
actual_port="$(kubectl -n "${NAMESPACE}" get service "${SERVICE_NAME}" -o jsonpath='{.spec.ports[0].port}')"
if [[ "${actual_port}" != "${PORT}" ]]; then
  echo "ERROR: Service ${SERVICE_NAME} listens on ${actual_port}, expected ${PORT}" >&2
  exit 1
fi

echo "Checking Deployment ${DEPLOYMENT_NAME} rollout..."
kubectl -n "${NAMESPACE}" rollout status "deployment/${DEPLOYMENT_NAME}" --timeout=180s >/dev/null

pod_name="$(kubectl -n "${NAMESPACE}" get pods -l app.kubernetes.io/instance="${DEPLOYMENT_NAME}" -o jsonpath='{.items[0].metadata.name}')"
if [[ -z "${pod_name}" ]]; then
  echo "ERROR: No pod found for ${DEPLOYMENT_NAME}" >&2
  exit 1
fi

echo "Checking model mount in pod ${pod_name}..."
kubectl -n "${NAMESPACE}" exec "${pod_name}" -- sh -lc 'test -s /models/ada.tflite && test -s /models/hey_ada.tflite'

echo "Wake-word runtime smoke checks passed."
