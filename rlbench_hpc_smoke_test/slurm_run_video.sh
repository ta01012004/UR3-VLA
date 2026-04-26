#!/usr/bin/env bash
#SBATCH --job-name=rlbench-video
#SBATCH --output=rlbench-video-%j.out
#SBATCH --error=rlbench-video-%j.err
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --partition=gpu
#SBATCH --account=ddt_acc23
#SBATCH --gres=gpu:1

set -euo pipefail

# Adjust these for your cluster if needed:
#   sbatch --partition=<gpu-partition> --account=<account> slurm_run_video.sh
#   module load anaconda3 cuda xvfb

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

if [ ! -f "${COPPELIASIM_ROOT}/coppeliaSim.sh" ]; then
  echo "[error] CoppeliaSim not found: ${COPPELIASIM_ROOT}/coppeliaSim.sh" >&2
  echo "[error] Run bash install_hpc.sh first, or export COPPELIASIM_ROOT to an existing CoppeliaSim 4.1.0 install." >&2
  exit 1
fi
if [ ! -e "${COPPELIASIM_ROOT}/libcoppeliaSim.so.1" ] && [ -e "${COPPELIASIM_ROOT}/libcoppeliaSim.so" ]; then
  ln -s libcoppeliaSim.so "${COPPELIASIM_ROOT}/libcoppeliaSim.so.1"
fi

CONDA_ENV_NAME="${CONDA_ENV_NAME:-rlbench-hpc}"
if ! python - <<'PY' >/dev/null 2>&1
import rlbench, pyrep
PY
then
  if command -v conda >/dev/null 2>&1; then
    # shellcheck disable=SC1091
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate "${CONDA_ENV_NAME}"
  elif [ -n "${CONDA_EXE:-}" ]; then
    # shellcheck disable=SC1091
    source "$(dirname "$(dirname "${CONDA_EXE}")")/etc/profile.d/conda.sh"
    conda activate "${CONDA_ENV_NAME}"
  elif [ -f "${HOME}/miniconda3/etc/profile.d/conda.sh" ]; then
    # shellcheck disable=SC1091
    source "${HOME}/miniconda3/etc/profile.d/conda.sh"
    conda activate "${CONDA_ENV_NAME}"
  elif [ -f "${HOME}/anaconda3/etc/profile.d/conda.sh" ]; then
    # shellcheck disable=SC1091
    source "${HOME}/anaconda3/etc/profile.d/conda.sh"
    conda activate "${CONDA_ENV_NAME}"
  else
    echo "[error] rlbench/pyrep not importable and conda was not found." >&2
    echo "[error] Activate your env first or edit this script's module/conda lines." >&2
    exit 1
  fi
fi

python - <<'PY'
import sys, rlbench, pyrep
print('[check] Python:', sys.version)
print('[check] RLBench:', rlbench.__file__)
print('[check] PyRep:', pyrep.__file__)
PY

cd "${ROOT_DIR}"
RLBENCH_TASK="${RLBENCH_TASK:-pick_up_cup}"
OUT_DIR="outputs/${SLURM_JOB_ID:-local}_${RLBENCH_TASK}"
PY_CMD=(python run_rlbench_video.py --out "${OUT_DIR}" --task "${RLBENCH_TASK}" --camera front_rgb --fps 20)

if [ -n "${DISPLAY:-}" ]; then
  echo "[run] DISPLAY=${DISPLAY}; running directly."
  "${PY_CMD[@]}"
elif command -v xvfb-run >/dev/null 2>&1; then
  echo "[run] DISPLAY not set; using xvfb-run fallback."
  xvfb-run -a -s "-screen 0 1280x1024x24" "${PY_CMD[@]}"
elif command -v Xvfb >/dev/null 2>&1; then
  XVFB_DISPLAY=":${XVFB_DISPLAY_NUM:-$((90 + (${SLURM_JOB_ID:-0} % 1000)))}"
  echo "[run] DISPLAY not set; starting Xvfb on ${XVFB_DISPLAY}."
  if [ -z "${XDG_RUNTIME_DIR:-}" ] || [ ! -d "${XDG_RUNTIME_DIR}" ] || [ ! -w "${XDG_RUNTIME_DIR}" ]; then
    export XDG_RUNTIME_DIR="${TMPDIR:-/tmp}/xdg-runtime-${USER}-${SLURM_JOB_ID:-local}"
  fi
  mkdir -p "${XDG_RUNTIME_DIR}"
  chmod 700 "${XDG_RUNTIME_DIR}" || true
  Xvfb "${XVFB_DISPLAY}" -screen 0 1280x1024x24 -ac +render -noreset &
  XVFB_PID=$!
  cleanup_xvfb() {
    kill "${XVFB_PID}" >/dev/null 2>&1 || true
  }
  trap cleanup_xvfb EXIT
  sleep 3
  if ! kill -0 "${XVFB_PID}" >/dev/null 2>&1; then
    echo "[error] Xvfb failed to start on ${XVFB_DISPLAY}." >&2
    exit 1
  fi
  export DISPLAY="${XVFB_DISPLAY}"
  "${PY_CMD[@]}"
else
  echo "[error] DISPLAY is not set and neither xvfb-run nor Xvfb is available." >&2
  echo "[error] Ask HPC admin for GPU-backed X/VirtualGL/EGL, or load/install Xvfb." >&2
  exit 1
fi
