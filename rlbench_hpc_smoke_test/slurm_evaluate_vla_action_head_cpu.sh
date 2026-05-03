#!/usr/bin/env bash
#SBATCH --job-name=rlbench-vla-eval-cpu
#SBATCH --output=rlbench-vla-eval-cpu-%j.out
#SBATCH --error=rlbench-vla-eval-cpu-%j.err
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
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

python evaluate_vla_action_head.py \
  --dataset "${RLBENCH_DATASET_OUT:-datasets/rlbench_vla_from_videos}" \
  --checkpoint "${VLA_CHECKPOINT_OUT:-checkpoints/tiny_vla_action_head_from_videos.pt}" \
  --split "${VLA_EVAL_SPLIT:-val}" \
  --samples "${VLA_EVAL_SAMPLES:-5}"
