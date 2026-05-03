#!/usr/bin/env bash
#SBATCH --job-name=rlbench-vla-data
#SBATCH --output=rlbench-vla-data-%j.out
#SBATCH --error=rlbench-vla-data-%j.err
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --partition=gpu
#SBATCH --account=ddt_acc23
#SBATCH --gres=gpu:1

set -euo pipefail

if [ -n "${SLURM_SUBMIT_DIR:-}" ]; then
  ROOT_DIR="${SLURM_SUBMIT_DIR}"
else
  ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

GLIBC_VERSION_OUTPUT="$(ldd --version 2>&1)"
GLIBC_VERSION_LINE="${GLIBC_VERSION_OUTPUT%%$'\n'*}"
GLIBC_MINOR="$(sed -E 's/.* ([0-9]+)\.([0-9]+).*/\2/' <<<"${GLIBC_VERSION_LINE}")"
if [ "${GLIBC_MINOR}" -lt 29 ]; then
  COPPELIASIM_DISTRO="Ubuntu18_04"
else
  COPPELIASIM_DISTRO="Ubuntu20_04"
fi

COPPELIASIM_DIR="CoppeliaSim_Edu_V4_1_0_${COPPELIASIM_DISTRO}"
export COPPELIASIM_ROOT="${COPPELIASIM_ROOT:-${ROOT_DIR}/third_party/${COPPELIASIM_DIR}}"
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-}:${COPPELIASIM_ROOT}"
export QT_QPA_PLATFORM_PLUGIN_PATH="${COPPELIASIM_ROOT}"

CONDA_ENV_NAME="${CONDA_ENV_NAME:-rlbench-hpc}"
if ! python - <<'PY' >/dev/null 2>&1
import rlbench, pyrep
PY
then
  if command -v conda >/dev/null 2>&1; then
    # shellcheck disable=SC1091
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate "${CONDA_ENV_NAME}"
  elif [ -f "${HOME}/miniconda3/etc/profile.d/conda.sh" ]; then
    # shellcheck disable=SC1091
    source "${HOME}/miniconda3/etc/profile.d/conda.sh"
    conda activate "${CONDA_ENV_NAME}"
  else
    echo "[error] conda not found and rlbench/pyrep are not importable." >&2
    exit 1
  fi
fi

cd "${ROOT_DIR}"

TASKS="${RLBENCH_TASKS:-slide_block_to_target,pick_up_cup}"
EPISODES_PER_TASK="${RLBENCH_EPISODES_PER_TASK:-20}"
DATASET_OUT="${RLBENCH_DATASET_OUT:-datasets/rlbench_vla}"
CAMERAS="${RLBENCH_CAMERAS:-front_rgb,wrist_rgb}"

PY_CMD=(
  python collect_vla_dataset.py
  --out "${DATASET_OUT}"
  --tasks "${TASKS}"
  --episodes-per-task "${EPISODES_PER_TASK}"
  --cameras "${CAMERAS}"
  --robot-setup "${RLBENCH_ROBOT_SETUP:-panda}"
)

if [ -n "${DISPLAY:-}" ]; then
  echo "[run] DISPLAY=${DISPLAY}; running directly."
  "${PY_CMD[@]}"
elif command -v xvfb-run >/dev/null 2>&1; then
  echo "[run] DISPLAY not set; using xvfb-run fallback."
  xvfb-run -a -s "-screen 0 1280x1024x24" "${PY_CMD[@]}"
elif command -v Xvfb >/dev/null 2>&1; then
  XVFB_DISPLAY=":${XVFB_DISPLAY_NUM:-$((100 + (${SLURM_JOB_ID:-0} % 1000)))}"
  echo "[run] DISPLAY not set; starting Xvfb on ${XVFB_DISPLAY}."
  export XDG_RUNTIME_DIR="${TMPDIR:-/tmp}/xdg-runtime-${USER}-${SLURM_JOB_ID:-local}"
  mkdir -p "${XDG_RUNTIME_DIR}"
  chmod 700 "${XDG_RUNTIME_DIR}" || true
  Xvfb "${XVFB_DISPLAY}" -screen 0 1280x1024x24 -ac +render -noreset &
  XVFB_PID=$!
  trap 'kill "${XVFB_PID}" >/dev/null 2>&1 || true' EXIT
  sleep 3
  export DISPLAY="${XVFB_DISPLAY}"
  "${PY_CMD[@]}"
else
  echo "[error] DISPLAY is not set and neither xvfb-run nor Xvfb is available." >&2
  exit 1
fi
