#!/usr/bin/env bash
#SBATCH --job-name=smolvla-ft
#SBATCH --output=smolvla-ft-%j.out
#SBATCH --error=smolvla-ft-%j.err
#SBATCH --time=04:00:00
#SBATCH --cpus-per-task=6
#SBATCH --mem=48G
#SBATCH --gres=gpu:1
#SBATCH --partition=gpu
#SBATCH --account=ddt_acc23

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${RLBENCH_WORK_DIR:-${SCRIPT_DIR}}"

ENV_NAME="${SMOLVLA_ENV_NAME:-smolvla-hpc}"
DATASET_SRC="${RLBENCH_DATASET_SRC:-datasets/rlbench_vla_slide_100ep}"
HF_LEROBOT_HOME="${HF_LEROBOT_HOME:-${HOME}/.cache/huggingface/lerobot}"
LEROBOT_REPO_ID="${LEROBOT_REPO_ID:-ta01012004/rlbench_slide_block_to_target_100ep}"
OUTPUT_DIR="${SMOLVLA_OUTPUT_DIR:-${ROOT_DIR}/checkpoints/smolvla_slide_100ep}"
STEPS="${SMOLVLA_STEPS:-200}"
BATCH_SIZE="${SMOLVLA_BATCH_SIZE:-4}"

if command -v conda >/dev/null 2>&1; then
  # shellcheck disable=SC1091
  source "$(conda info --base)/etc/profile.d/conda.sh"
else
  # shellcheck disable=SC1091
  source "${HOME}/miniconda3/etc/profile.d/conda.sh"
fi
conda activate "${ENV_NAME}"

cd "${ROOT_DIR}"
export HF_LEROBOT_HOME
export TOKENIZERS_PARALLELISM=false
export WANDB_MODE=disabled

python - <<'PY'
import torch
print("[check] torch:", torch.__version__)
print("[check] cuda:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("[check] gpu:", torch.cuda.get_device_name(0))
PY

if [ ! -d "${HF_LEROBOT_HOME}/${LEROBOT_REPO_ID}/meta" ]; then
  python convert_rlbench_to_lerobot.py \
    --src "${DATASET_SRC}" \
    --repo-id "${LEROBOT_REPO_ID}" \
    --hf-lerobot-home "${HF_LEROBOT_HOME}" \
    --split steps \
    --overwrite
fi

lerobot-train \
  --policy.path=lerobot/smolvla_base \
  --dataset.repo_id="${LEROBOT_REPO_ID}" \
  --batch_size="${BATCH_SIZE}" \
  --steps="${STEPS}" \
  --save_freq="${STEPS}" \
  --eval_freq=0 \
  --log_freq=10 \
  --output_dir="${OUTPUT_DIR}" \
  --job_name=smolvla_rlbench_slide_100ep \
  --policy.device=cuda \
  --wandb.enable=false

python test_smolvla_checkpoint.py \
  --dataset-repo-id "${LEROBOT_REPO_ID}" \
  --checkpoint-dir "${OUTPUT_DIR}" \
  --hf-lerobot-home "${HF_LEROBOT_HOME}"
