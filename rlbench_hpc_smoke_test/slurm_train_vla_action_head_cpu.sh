#!/usr/bin/env bash
#SBATCH --job-name=rlbench-vla-train-cpu
#SBATCH --output=rlbench-vla-train-cpu-%j.out
#SBATCH --error=rlbench-vla-train-cpu-%j.err
#SBATCH --time=01:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --partition=normal
#SBATCH --account=ddt_acc23

set -euo pipefail

if [ -n "${SLURM_SUBMIT_DIR:-}" ]; then
  ROOT_DIR="${SLURM_SUBMIT_DIR}"
else
  ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

CONDA_ENV_NAME="${CONDA_ENV_NAME:-rlbench-hpc}"
if command -v conda >/dev/null 2>&1; then
  # shellcheck disable=SC1091
  source "$(conda info --base)/etc/profile.d/conda.sh"
  conda activate "${CONDA_ENV_NAME}"
elif [ -f "${HOME}/miniconda3/etc/profile.d/conda.sh" ]; then
  # shellcheck disable=SC1091
  source "${HOME}/miniconda3/etc/profile.d/conda.sh"
  conda activate "${CONDA_ENV_NAME}"
fi

cd "${ROOT_DIR}"

python - <<'PY'
import torch
print("[check] torch:", torch.__version__)
print("[check] cuda:", torch.cuda.is_available())
PY

python train_vla_action_head.py \
  --dataset "${RLBENCH_DATASET_OUT:-datasets/rlbench_vla_from_videos}" \
  --out "${VLA_CHECKPOINT_OUT:-checkpoints/tiny_vla_action_head.pt}" \
  --epochs "${VLA_EPOCHS:-5}" \
  --batch-size "${VLA_BATCH_SIZE:-64}"
