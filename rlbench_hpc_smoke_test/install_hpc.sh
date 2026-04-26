#!/usr/bin/env bash
set -euo pipefail

# install_hpc.sh
# Usage on HPC login/compute node:
#   conda create -n rlbench-hpc python=3.8 -y
#   conda activate rlbench-hpc
#   bash install_hpc.sh
#
# If your cluster blocks downloads from compute nodes, run this on a login node
# or download CoppeliaSim manually and set COPPELIASIM_ROOT yourself.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THIRD_PARTY="${ROOT_DIR}/third_party"
mkdir -p "${THIRD_PARTY}"

PY_MINOR="$(python - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)"
if [ "${PY_MINOR}" != "3.8" ]; then
  echo "[warn] Current Python is ${PY_MINOR}. PyRep/RLBench is old; Python 3.8.x is safest."
  echo "[warn] Continue only if your HPC has already validated another Python version."
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
export COPPELIASIM_ROOT="${COPPELIASIM_ROOT:-${THIRD_PARTY}/${COPPELIASIM_DIR}}"
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-}:${COPPELIASIM_ROOT}"
export QT_QPA_PLATFORM_PLUGIN_PATH="${COPPELIASIM_ROOT}"

if [ ! -d "${COPPELIASIM_ROOT}" ] || [ ! -f "${COPPELIASIM_ROOT}/coppeliaSim.sh" ]; then
  echo "[install] Downloading CoppeliaSim 4.1.0 to ${COPPELIASIM_ROOT}"
  cd "${THIRD_PARTY}"
  wget -nc "https://downloads.coppeliarobotics.com/V4_1_0/${COPPELIASIM_DIR}.tar.xz"
  mkdir -p "${COPPELIASIM_ROOT}"
  tar -xf "${COPPELIASIM_DIR}.tar.xz" -C "${COPPELIASIM_ROOT}" --strip-components 1
else
  echo "[install] Using existing COPPELIASIM_ROOT=${COPPELIASIM_ROOT}"
fi

if [ ! -f "${COPPELIASIM_ROOT}/coppeliaSim.sh" ]; then
  echo "[error] CoppeliaSim not found at ${COPPELIASIM_ROOT}/coppeliaSim.sh" >&2
  exit 1
fi
if [ ! -e "${COPPELIASIM_ROOT}/libcoppeliaSim.so.1" ] && [ -e "${COPPELIASIM_ROOT}/libcoppeliaSim.so" ]; then
  ln -s libcoppeliaSim.so "${COPPELIASIM_ROOT}/libcoppeliaSim.so.1"
fi

cd "${ROOT_DIR}"
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
if command -v conda >/dev/null 2>&1 && [ -n "${CONDA_PREFIX:-}" ]; then
  conda install -y xorg-xserver-xvfb
else
  echo "[warn] conda env not detected; skipping conda Xvfb install."
  echo "[warn] Install Xvfb manually if your node has no DISPLAY/xvfb-run."
fi

# Pinned to HEAD observed during scaffold creation for reproducibility.
PYREP_COMMIT="${PYREP_COMMIT:-8f420be8064b1970aae18a9cfbc978dfb15747ef}"
RLBENCH_COMMIT="${RLBENCH_COMMIT:-02720bba4c73fe02eb75df946b8791b806028a9d}"
python -m pip install --no-cache-dir "pyrep @ git+https://github.com/stepjam/PyRep.git@${PYREP_COMMIT}"
python -m pip install --no-cache-dir --no-deps "rlbench @ git+https://github.com/stepjam/RLBench.git@${RLBENCH_COMMIT}"

python - <<'PY'
import rlbench, pyrep
print('[check] rlbench import OK:', rlbench.__file__)
print('[check] pyrep import OK:', pyrep.__file__)
PY

cat <<EOF

[install] Done.
Add these to your job script before running Python:
  export COPPELIASIM_ROOT=${COPPELIASIM_ROOT}
  export LD_LIBRARY_PATH=\$LD_LIBRARY_PATH:\$COPPELIASIM_ROOT
  export QT_QPA_PLATFORM_PLUGIN_PATH=\$COPPELIASIM_ROOT

For rendering on a headless HPC node you still need an X server/GPU display.
Try one of:
  xvfb-run -a -s "-screen 0 1280x1024x24" python run_rlbench_video.py
or, on NVIDIA GPU nodes configured by admin:
  export DISPLAY=:99
  python run_rlbench_video.py
EOF
