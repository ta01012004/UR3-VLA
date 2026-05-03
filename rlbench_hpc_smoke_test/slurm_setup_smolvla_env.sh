#!/usr/bin/env bash
#SBATCH --job-name=smolvla-setup
#SBATCH --output=smolvla-setup-%j.out
#SBATCH --error=smolvla-setup-%j.err
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --partition=normal
#SBATCH --account=ddt_acc23

set -euo pipefail

ENV_NAME="${SMOLVLA_ENV_NAME:-smolvla-hpc}"
LEROBOT_DIR="${LEROBOT_DIR:-${HOME}/src/lerobot}"

if command -v conda >/dev/null 2>&1; then
  # shellcheck disable=SC1091
  source "$(conda info --base)/etc/profile.d/conda.sh"
else
  # shellcheck disable=SC1091
  source "${HOME}/miniconda3/etc/profile.d/conda.sh"
fi

if ! conda env list | awk '{print $1}' | grep -qx "${ENV_NAME}"; then
  conda create -y -n "${ENV_NAME}" python=3.12
fi
conda activate "${ENV_NAME}"

conda install -y -c conda-forge ffmpeg
python -m pip install --upgrade pip wheel setuptools

mkdir -p "$(dirname "${LEROBOT_DIR}")"
if [ ! -d "${LEROBOT_DIR}/.git" ]; then
  git clone https://github.com/huggingface/lerobot.git "${LEROBOT_DIR}"
else
  git -C "${LEROBOT_DIR}" pull --ff-only
fi

python -m pip install -e "${LEROBOT_DIR}[smolvla,dataset]"
python - <<'PY'
import torch
import lerobot
print("[check] lerobot:", getattr(lerobot, "__version__", "source"))
print("[check] torch:", torch.__version__)
print("[check] cuda:", torch.cuda.is_available())
PY
