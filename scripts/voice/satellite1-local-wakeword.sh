#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORKFLOW_DIR="${ROOT_DIR}/scripts/voice/satellite1"
ENV_FILE="${SATELLITE1_ENV_FILE:-${ROOT_DIR}/scripts/voice/satellite1-wakeword.env}"

if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
fi

default_cache_root() {
  if [[ "${OSTYPE}" == darwin* ]]; then
    echo "${HOME}/Library/Caches/home-ops"
  else
    echo "${XDG_CACHE_HOME:-${HOME}/.cache}/home-ops"
  fi
}

CACHE_ROOT="${SATELLITE1_CACHE_ROOT:-$(default_cache_root)}"
SATELLITE1_FIRMWARE_REF="${SATELLITE1_FIRMWARE_REF:-develop}"
SATELLITE1_MICRO_WAKE_WORD_REF="${SATELLITE1_MICRO_WAKE_WORD_REF:-main}"

SATELLITE1_FIRMWARE_DIR="${SATELLITE1_FIRMWARE_DIR:-${CACHE_ROOT}/Satellite1-ESPHome}"
MICRO_WAKE_WORD_DIR="${SATELLITE1_MICRO_WAKE_WORD_DIR:-${CACHE_ROOT}/micro-wake-word}"
PIPER_SAMPLE_GENERATOR_DIR="${SATELLITE1_PIPER_SAMPLE_GENERATOR_DIR:-${CACHE_ROOT}/piper-sample-generator}"

MODELS_DIR="${SATELLITE1_MODELS_DIR:-${WORKFLOW_DIR}/models}"
SAMPLES_DIR="${SATELLITE1_SAMPLES_DIR:-${WORKFLOW_DIR}/samples}"
TRAINING_DIR="${SATELLITE1_TRAINING_DIR:-${WORKFLOW_DIR}/training}"

FIRMWARE_MODELS_DIR_REL="${SATELLITE1_FIRMWARE_MODELS_DIR_REL:-config/home_ops_models}"
FIRMWARE_MODELS_DIR="${SATELLITE1_FIRMWARE_DIR}/${FIRMWARE_MODELS_DIR_REL}"

MODEL_AUTHOR="${SATELLITE1_MODEL_AUTHOR:-Andrew McCall}"
MODEL_WEBSITE="${SATELLITE1_MODEL_WEBSITE:-https://github.com/andrewmccall/home-ops}"
MODEL_LANGUAGES="${SATELLITE1_MODEL_LANGUAGES:-en}"
MODEL_MINIMUM_ESPHOME_VERSION="${SATELLITE1_MODEL_MINIMUM_ESPHOME_VERSION:-2026.2.0}"

ADA_PROBABILITY_CUTOFF="${SATELLITE1_ADA_PROBABILITY_CUTOFF:-0.85}"
ADA_SLIDING_WINDOW_SIZE="${SATELLITE1_ADA_SLIDING_WINDOW_SIZE:-5}"
ADA_TENSOR_ARENA_SIZE="${SATELLITE1_ADA_TENSOR_ARENA_SIZE:-45672}"

HEY_ADA_PROBABILITY_CUTOFF="${SATELLITE1_HEY_ADA_PROBABILITY_CUTOFF:-0.90}"
HEY_ADA_SLIDING_WINDOW_SIZE="${SATELLITE1_HEY_ADA_SLIDING_WINDOW_SIZE:-5}"
HEY_ADA_TENSOR_ARENA_SIZE="${SATELLITE1_HEY_ADA_TENSOR_ARENA_SIZE:-45672}"

info() {
  printf '==> %s\n' "$*"
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}

ensure_dirs() {
  mkdir -p \
    "${CACHE_ROOT}" \
    "${MODELS_DIR}" \
    "${SAMPLES_DIR}/ada" \
    "${SAMPLES_DIR}/hey_ada" \
    "${SAMPLES_DIR}/negative" \
    "${SAMPLES_DIR}/background" \
    "${TRAINING_DIR}"
}

clone_or_update() {
  local repo_url="$1"
  local repo_dir="$2"
  local repo_ref="$3"

  if [[ ! -d "${repo_dir}/.git" ]]; then
    info "Cloning ${repo_url} @ ${repo_ref}"
    git clone --depth 1 --branch "${repo_ref}" "${repo_url}" "${repo_dir}"
    return
  fi

  info "Updating ${repo_dir} to ${repo_ref}"
  git -C "${repo_dir}" remote set-url origin "${repo_url}"
  git -C "${repo_dir}" fetch --depth 1 origin "${repo_ref}"
  git -C "${repo_dir}" checkout --force FETCH_HEAD >/dev/null
}

choose_training_python() {
  local candidate
  if [[ -n "${SATELLITE1_TRAINING_PYTHON:-}" ]]; then
    candidate="${SATELLITE1_TRAINING_PYTHON}"
  elif command -v python3.10 >/dev/null 2>&1; then
    candidate="python3.10"
  else
    candidate="python3"
  fi

  require_command "${candidate}"

  "${candidate}" - <<'PY' >/dev/null 2>&1 || die "Training Python must be Python 3.10.x. Override with SATELLITE1_TRAINING_PYTHON."
import sys
raise SystemExit(0 if sys.version_info[:2] == (3, 10) else 1)
PY

  echo "${candidate}"
}

setup_micro_wake_word_env() {
  local python_bin
  python_bin="$(choose_training_python)"

  clone_or_update "https://github.com/OHF-Voice/micro-wake-word.git" "${MICRO_WAKE_WORD_DIR}" "${SATELLITE1_MICRO_WAKE_WORD_REF}"

  if [[ ! -d "${MICRO_WAKE_WORD_DIR}/.venv" ]]; then
    info "Creating microWakeWord venv with ${python_bin}"
    "${python_bin}" -m venv "${MICRO_WAKE_WORD_DIR}/.venv"
  fi

  # shellcheck disable=SC1091
  source "${MICRO_WAKE_WORD_DIR}/.venv/bin/activate"

  info "Installing microWakeWord dependencies"
  pip install --upgrade pip setuptools wheel
  if [[ "${OSTYPE}" == darwin* ]]; then
    pip install 'git+https://github.com/puddly/pymicro-features@puddly/minimum-cpp-version'
  fi
  pip install 'git+https://github.com/whatsnowplaying/audio-metadata@d4ebb238e6a401bb1a5aaaac60c9e2b3cb30929f'
  pip install -e "${MICRO_WAKE_WORD_DIR}" jupyterlab torch torchaudio piper-phonemize-cross==1.2.1

  if [[ "${OSTYPE}" == darwin* ]]; then
    clone_or_update "https://github.com/kahrendt/piper-sample-generator.git" "${PIPER_SAMPLE_GENERATOR_DIR}" "mps-support"
  else
    clone_or_update "https://github.com/rhasspy/piper-sample-generator.git" "${PIPER_SAMPLE_GENERATOR_DIR}" "master"
  fi
}

setup_firmware_env() {
  clone_or_update "https://github.com/FutureProofHomes/Satellite1-ESPHome.git" "${SATELLITE1_FIRMWARE_DIR}" "${SATELLITE1_FIRMWARE_REF}"
  info "Installing Satellite1 firmware build dependencies"
  (
    cd "${SATELLITE1_FIRMWARE_DIR}"
    # shellcheck disable=SC1091
    source scripts/setup_build_env.sh
  )
}

prepare_training_workspace() {
  ensure_dirs
  [[ -f "${MICRO_WAKE_WORD_DIR}/notebooks/basic_training_notebook.ipynb" ]] || die "Run setup first so the micro-wake-word repo is available."

  cp "${MICRO_WAKE_WORD_DIR}/notebooks/basic_training_notebook.ipynb" "${TRAINING_DIR}/basic_training_notebook.ipynb"
  cat > "${TRAINING_DIR}/local_paths.txt" <<EOF
Satellite1 local training paths
===============================

Training notebook:
${TRAINING_DIR}/basic_training_notebook.ipynb

microWakeWord repo:
${MICRO_WAKE_WORD_DIR}

Piper sample generator repo:
${PIPER_SAMPLE_GENERATOR_DIR}

Model output staging:
${MODELS_DIR}

Optional positive / negative sample staging:
${SAMPLES_DIR}/ada
${SAMPLES_DIR}/hey_ada
${SAMPLES_DIR}/negative
${SAMPLES_DIR}/background

Suggested local startup:
  source "${MICRO_WAKE_WORD_DIR}/.venv/bin/activate"
  jupyter lab "${TRAINING_DIR}/basic_training_notebook.ipynb"
EOF

  info "Prepared local training workspace in ${TRAINING_DIR}"
}

write_manifest() {
  local name=""
  local wake_word=""
  local input=""
  local output=""
  local author="${MODEL_AUTHOR}"
  local website="${MODEL_WEBSITE}"
  local languages="${MODEL_LANGUAGES}"
  local min_version="${MODEL_MINIMUM_ESPHOME_VERSION}"
  local cutoff=""
  local sliding_window=""
  local tensor_arena=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --name)
        name="$2"
        shift 2
        ;;
      --wake-word)
        wake_word="$2"
        shift 2
        ;;
      --input)
        input="$2"
        shift 2
        ;;
      --output)
        output="$2"
        shift 2
        ;;
      --author)
        author="$2"
        shift 2
        ;;
      --website)
        website="$2"
        shift 2
        ;;
      --languages)
        languages="$2"
        shift 2
        ;;
      --minimum-esphome-version)
        min_version="$2"
        shift 2
        ;;
      --cutoff)
        cutoff="$2"
        shift 2
        ;;
      --sliding-window-size)
        sliding_window="$2"
        shift 2
        ;;
      --tensor-arena-size)
        tensor_arena="$2"
        shift 2
        ;;
      *)
        die "Unknown manifest option: $1"
        ;;
    esac
  done

  [[ -n "${name}" ]] || die "manifest requires --name"
  [[ -n "${wake_word}" ]] || die "manifest requires --wake-word"
  [[ -n "${input}" ]] || die "manifest requires --input"
  [[ -f "${input}" ]] || die "Model file not found: ${input}"

  if [[ -z "${output}" ]]; then
    output="${MODELS_DIR}/${name}.json"
  fi

  case "${name}" in
    ada)
      cutoff="${cutoff:-${ADA_PROBABILITY_CUTOFF}}"
      sliding_window="${sliding_window:-${ADA_SLIDING_WINDOW_SIZE}}"
      tensor_arena="${tensor_arena:-${ADA_TENSOR_ARENA_SIZE}}"
      ;;
    hey_ada)
      cutoff="${cutoff:-${HEY_ADA_PROBABILITY_CUTOFF}}"
      sliding_window="${sliding_window:-${HEY_ADA_SLIDING_WINDOW_SIZE}}"
      tensor_arena="${tensor_arena:-${HEY_ADA_TENSOR_ARENA_SIZE}}"
      ;;
    *)
      cutoff="${cutoff:-0.85}"
      sliding_window="${sliding_window:-5}"
      tensor_arena="${tensor_arena:-45672}"
      ;;
  esac

  mkdir -p "$(dirname "${output}")"
  local copied_model="${MODELS_DIR}/${name}.tflite"
  cp "${input}" "${copied_model}"

  OUTPUT_PATH="${output}" \
  COPIED_MODEL_PATH="${copied_model}" \
  WAKE_WORD="${wake_word}" \
  AUTHOR="${author}" \
  WEBSITE="${website}" \
  LANGUAGES="${languages}" \
  MIN_VERSION="${min_version}" \
  CUTOFF="${cutoff}" \
  SLIDING_WINDOW="${sliding_window}" \
  TENSOR_ARENA="${tensor_arena}" \
  python3 <<'PY'
from pathlib import Path
import json
import os

output_path = Path(os.environ["OUTPUT_PATH"])
copied_model_path = Path(os.environ["COPIED_MODEL_PATH"])
languages = [part.strip() for part in os.environ["LANGUAGES"].split(",") if part.strip()]

manifest = {
    "type": "micro",
    "wake_word": os.environ["WAKE_WORD"],
    "author": os.environ["AUTHOR"],
    "website": os.environ["WEBSITE"],
    "model": copied_model_path.name,
    "trained_languages": languages or ["en"],
    "version": 2,
    "micro": {
        "probability_cutoff": float(os.environ["CUTOFF"]),
        "sliding_window_size": int(os.environ["SLIDING_WINDOW"]),
        "feature_step_size": 10,
        "tensor_arena_size": int(os.environ["TENSOR_ARENA"]),
        "minimum_esphome_version": os.environ["MIN_VERSION"],
    },
}

output_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY

  info "Wrote manifest ${output}"
}

copy_custom_models_into_firmware() {
  mkdir -p "${FIRMWARE_MODELS_DIR}"

  local required=(
    "${MODELS_DIR}/ada.json"
    "${MODELS_DIR}/ada.tflite"
    "${MODELS_DIR}/hey_ada.json"
    "${MODELS_DIR}/hey_ada.tflite"
  )

  local path
  for path in "${required[@]}"; do
    [[ -f "${path}" ]] || die "Missing required model asset: ${path}"
  done

  cp "${MODELS_DIR}/ada.json" "${FIRMWARE_MODELS_DIR}/ada.json"
  cp "${MODELS_DIR}/ada.tflite" "${FIRMWARE_MODELS_DIR}/ada.tflite"
  cp "${MODELS_DIR}/hey_ada.json" "${FIRMWARE_MODELS_DIR}/hey_ada.json"
  cp "${MODELS_DIR}/hey_ada.tflite" "${FIRMWARE_MODELS_DIR}/hey_ada.tflite"
}

patch_firmware_voice_assistant() {
  local target="${SATELLITE1_FIRMWARE_DIR}/config/common/voice_assistant.yaml"
  [[ -f "${target}" ]] || die "Missing firmware config: ${target}"

  TARGET_PATH="${target}" \
  MODEL_DIR_REL="${FIRMWARE_MODELS_DIR_REL}" \
  ADA_JSON_PATH="${FIRMWARE_MODELS_DIR}/ada.json" \
  HEY_ADA_JSON_PATH="${FIRMWARE_MODELS_DIR}/hey_ada.json" \
  python3 <<'PY'
from pathlib import Path
import json
import math
import os

target_path = Path(os.environ["TARGET_PATH"])
model_dir_rel = os.environ["MODEL_DIR_REL"].replace("\\", "/")

with open(os.environ["ADA_JSON_PATH"], encoding="utf-8") as handle:
    ada_manifest = json.load(handle)
with open(os.environ["HEY_ADA_JSON_PATH"], encoding="utf-8") as handle:
    hey_manifest = json.load(handle)


def quantize(probability: float) -> int:
    return max(1, min(255, int(probability * 255)))


def sensitivity_triplet(probability: float) -> tuple[int, int, int]:
    slight = probability
    moderate = max(probability - 0.08, 0.05)
    very = max(probability - 0.16, 0.05)
    return quantize(slight), quantize(moderate), quantize(very)


ada_slight, ada_moderate, ada_very = sensitivity_triplet(ada_manifest["micro"]["probability_cutoff"])
hey_slight, hey_moderate, hey_very = sensitivity_triplet(hey_manifest["micro"]["probability_cutoff"])

text = target_path.read_text(encoding="utf-8")

models_start = text.index("  models:\n", text.index("micro_wake_word:\n"))
models_end = text.index("  vad:\n", models_start)
models_block = (
    "  models:\n"
    f"    - model: {model_dir_rel}/ada.json\n"
    "      id: ada\n"
    f"    - model: {model_dir_rel}/hey_ada.json\n"
    "      id: hey_ada\n"
    "    - model: https://github.com/kahrendt/microWakeWord/releases/download/stop/stop.json\n"
    "      id: stop\n"
    "      internal: true\n"
)
text = text[:models_start] + models_block + text[models_end:]

select_start = text.index("select:\n")
select_block = f"""select:
  - platform: template
    id: mww_sensitivity_select
    name: "Wake word sensitivity"
    optimistic: true
    initial_option: Slightly sensitive
    restore_value: true
    entity_category: config
    options:
      - Slightly sensitive
      - Moderately sensitive
      - Very sensitive
    on_value:
      lambda: |-
        if (x == "Slightly sensitive") {{
          id(ada).set_probability_cutoff({ada_slight});      // {ada_manifest["micro"]["probability_cutoff"]:.2f}
          id(hey_ada).set_probability_cutoff({hey_slight});  // {hey_manifest["micro"]["probability_cutoff"]:.2f}
        }} else if (x == "Moderately sensitive") {{
          id(ada).set_probability_cutoff({ada_moderate});
          id(hey_ada).set_probability_cutoff({hey_moderate});
        }} else if (x == "Very sensitive") {{
          id(ada).set_probability_cutoff({ada_very});
          id(hey_ada).set_probability_cutoff({hey_very});
        }}
"""
text = text[:select_start] + select_block

target_path.write_text(text, encoding="utf-8")
PY

  info "Patched ${target} to use custom Ada / Hey Ada models"
}

install_models() {
  ensure_dirs
  [[ -d "${SATELLITE1_FIRMWARE_DIR}/.git" ]] || die "Run setup first so the Satellite1 firmware checkout exists."
  copy_custom_models_into_firmware
  patch_firmware_voice_assistant
}

ensure_firmware_venv() {
  [[ -f "${SATELLITE1_FIRMWARE_DIR}/.venv/bin/activate" ]] || die "Run setup first so the Satellite1 firmware venv exists."
}

run_esphome() {
  ensure_firmware_venv
  (
    cd "${SATELLITE1_FIRMWARE_DIR}"
    # shellcheck disable=SC1091
    source .venv/bin/activate
    esphome "$@"
  )
}

detect_serial_device() {
  local matches=()
  local candidate
  for candidate in /dev/cu.usbmodem* /dev/cu.usbserial* /dev/cu.SLAB* /dev/cu.wchusbserial* /dev/cu.wch*; do
    [[ -e "${candidate}" ]] || continue
    matches+=("${candidate}")
  done

  if [[ "${#matches[@]}" -eq 1 ]]; then
    echo "${matches[0]}"
  fi
}

choose_device_target() {
  local explicit="${1:-}"
  if [[ -n "${explicit}" ]]; then
    echo "${explicit}"
    return
  fi

  if [[ -n "${SATELLITE1_UPLOAD_DEVICE:-}" ]]; then
    echo "${SATELLITE1_UPLOAD_DEVICE}"
    return
  fi

  local usb_device
  usb_device="$(detect_serial_device || true)"
  if [[ -n "${usb_device}" ]]; then
    echo "${usb_device}"
    return
  fi

  if [[ -n "${SATELLITE1_UPLOAD_HOST:-}" ]]; then
    echo "${SATELLITE1_UPLOAD_HOST}"
    return
  fi

  die "No upload/log target found. Set SATELLITE1_UPLOAD_DEVICE, SATELLITE1_UPLOAD_HOST, or pass --device."
}

compile_firmware() {
  install_models
  info "Compiling Satellite1 firmware"
  run_esphome compile config/satellite1.yaml
}

upload_firmware() {
  local device=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --device)
        device="$2"
        shift 2
        ;;
      *)
        die "Unknown upload option: $1"
        ;;
    esac
  done

  install_models
  device="$(choose_device_target "${device}")"
  info "Uploading Satellite1 firmware via ${device}"
  run_esphome upload config/satellite1.yaml --device "${device}"
}

tail_logs() {
  local device=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --device)
        device="$2"
        shift 2
        ;;
      *)
        die "Unknown logs option: $1"
        ;;
    esac
  done

  device="$(choose_device_target "${device}")"
  info "Tailing Satellite1 logs via ${device}"
  run_esphome logs config/satellite1.yaml --device "${device}"
}

print_training_info() {
  cat <<EOF
Satellite1 local wake-word workflow

Local workflow root:
  ${WORKFLOW_DIR}

Models directory:
  ${MODELS_DIR}

Optional sample directories:
  ${SAMPLES_DIR}/ada
  ${SAMPLES_DIR}/hey_ada
  ${SAMPLES_DIR}/negative
  ${SAMPLES_DIR}/background

microWakeWord checkout:
  ${MICRO_WAKE_WORD_DIR}

Satellite1 firmware checkout:
  ${SATELLITE1_FIRMWARE_DIR}

Suggested local training start:
  source "${MICRO_WAKE_WORD_DIR}/.venv/bin/activate"
  jupyter lab "${TRAINING_DIR}/basic_training_notebook.ipynb"

The upstream notebook already includes background-noise, ambient-negative, and
reverb augmentation. Your own recorded positives/negatives can be staged in the
sample directories above for local experimentation.
EOF
}

print_help() {
  cat <<'EOF'
Usage: bash scripts/voice/satellite1-local-wakeword.sh <command> [options]

Commands:
  setup               Clone/update upstream repos and install local training/build dependencies.
  prepare-training    Copy the upstream microWakeWord notebook into repo-local training paths.
  manifest            Generate a microWakeWord manifest JSON for a trained TFLite model.
  install-models      Copy local Ada / Hey Ada models into the cloned Satellite1 firmware and patch voice_assistant.yaml.
  compile             Install custom models into the cloned firmware checkout and run `esphome compile`.
  upload [--device]   Install custom models and run `esphome upload` against USB or OTA target.
  logs [--device]     Tail ESPHome logs over the chosen USB or OTA target.
  training-info       Print the local notebook, model, and sample paths.
  help                Show this help text.

Examples:
  bash scripts/voice/satellite1-local-wakeword.sh setup
  bash scripts/voice/satellite1-local-wakeword.sh prepare-training
  bash scripts/voice/satellite1-local-wakeword.sh manifest --name ada --wake-word "Ada" --input scripts/voice/satellite1/models/ada.tflite
  bash scripts/voice/satellite1-local-wakeword.sh manifest --name hey_ada --wake-word "Hey Ada" --input scripts/voice/satellite1/models/hey_ada.tflite
  bash scripts/voice/satellite1-local-wakeword.sh compile
  bash scripts/voice/satellite1-local-wakeword.sh upload --device /dev/cu.usbmodem12345
EOF
}

main() {
  ensure_dirs
  require_command git
  require_command python3

  local command="${1:-help}"
  shift || true

  case "${command}" in
    setup)
      require_command pip3
      setup_micro_wake_word_env
      setup_firmware_env
      ;;
    prepare-training)
      prepare_training_workspace
      ;;
    manifest)
      write_manifest "$@"
      ;;
    install-models)
      install_models
      ;;
    compile)
      compile_firmware "$@"
      ;;
    upload)
      upload_firmware "$@"
      ;;
    logs)
      tail_logs "$@"
      ;;
    training-info)
      print_training_info
      ;;
    help|-h|--help)
      print_help
      ;;
    *)
      die "Unknown command: ${command}"
      ;;
  esac
}

main "$@"
