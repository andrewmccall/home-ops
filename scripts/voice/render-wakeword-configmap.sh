#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_DIR="${ROOT_DIR}/cluster/apps/house/wyoming-openwakeword"
MODEL_DIR="${APP_DIR}/models"
CONFIGMAP_PATH="${APP_DIR}/wakeword-models.yaml"
METADATA_PATH="${MODEL_DIR}/MODEL.md"

require_file() {
  local path="$1"
  if [[ ! -s "${path}" ]]; then
    echo "ERROR: Required model artifact missing or empty: ${path}" >&2
    exit 1
  fi
}

require_file "${MODEL_DIR}/ada.tflite"
require_file "${MODEL_DIR}/hey_ada.tflite"

ADA_SHA="$(shasum -a 256 "${MODEL_DIR}/ada.tflite" | awk '{print $1}')"
HEY_ADA_SHA="$(shasum -a 256 "${MODEL_DIR}/hey_ada.tflite" | awk '{print $1}')"
ADA_B64="$(base64 < "${MODEL_DIR}/ada.tflite" | tr -d '\n')"
HEY_ADA_B64="$(base64 < "${MODEL_DIR}/hey_ada.tflite" | tr -d '\n')"

tmp_configmap="$(mktemp)"
cat > "${tmp_configmap}" <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: wakeword-models
  namespace: house
  annotations:
    home-ops/ada-sha256: ${ADA_SHA}
    home-ops/hey-ada-sha256: ${HEY_ADA_SHA}
binaryData:
  ada.tflite: ${ADA_B64}
  hey_ada.tflite: ${HEY_ADA_B64}
EOF
mv "${tmp_configmap}" "${CONFIGMAP_PATH}"

if [[ -f "${METADATA_PATH}" ]]; then
  METADATA_PATH="${METADATA_PATH}" ADA_SHA="${ADA_SHA}" HEY_ADA_SHA="${HEY_ADA_SHA}" python3 <<'PY'
from pathlib import Path
import os

metadata_path = Path(os.environ["METADATA_PATH"])
ada_sha = os.environ["ADA_SHA"]
hey_ada_sha = os.environ["HEY_ADA_SHA"]
lines = metadata_path.read_text().splitlines()
updated = []
for line in lines:
    stripped = line.strip()
    if stripped.startswith("- ada.tflite:"):
        updated.append("  - ada.tflite: " + ada_sha)
    elif stripped.startswith("- hey_ada.tflite:"):
        updated.append("  - hey_ada.tflite: " + hey_ada_sha)
    else:
        updated.append(line)
metadata_path.write_text("\n".join(updated) + "\n")
PY
fi

echo "Rendered ${CONFIGMAP_PATH}"
echo "  ada.tflite    ${ADA_SHA}"
echo "  hey_ada.tflite ${HEY_ADA_SHA}"
