#!/usr/bin/env python3
"""Smoke-test a SmolVLA checkpoint and one local LeRobot dataset sample."""
import argparse
from pathlib import Path


def _find_policy_path(output_dir):
    output_dir = Path(output_dir)
    candidates = [
        output_dir / "checkpoints" / "last" / "pretrained_model",
        output_dir / "checkpoints" / "last",
        output_dir,
    ]
    for candidate in candidates:
        if (candidate / "config.json").exists():
            return candidate
    matches = sorted(output_dir.glob("**/pretrained_model/config.json"))
    if matches:
        return matches[-1].parent
    raise FileNotFoundError(f"Could not find a saved policy config under {output_dir}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-repo-id", default="ta01012004/rlbench_slide_block_to_target_100ep")
    parser.add_argument("--checkpoint-dir", default="checkpoints/smolvla_slide_100ep")
    parser.add_argument("--hf-lerobot-home", default="datasets/lerobot_cache")
    args = parser.parse_args()

    import os

    os.environ["HF_LEROBOT_HOME"] = str(Path(args.hf_lerobot_home).resolve())

    import torch
    from lerobot.datasets.lerobot_dataset import LeRobotDataset
    from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy

    dataset = LeRobotDataset(args.dataset_repo_id)
    sample = dataset[0]
    policy_path = _find_policy_path(args.checkpoint_dir)
    policy = SmolVLAPolicy.from_pretrained(str(policy_path))
    policy.eval()

    print(f"[test] dataset={args.dataset_repo_id}")
    print(f"[test] frames={dataset.num_frames} episodes={dataset.num_episodes}")
    print(f"[test] policy_path={policy_path}")
    print(f"[test] sample_keys={sorted(sample.keys())}")
    print(f"[test] cuda={torch.cuda.is_available()}")
    print("[ok] SmolVLA checkpoint and LeRobot dataset are loadable.")


if __name__ == "__main__":
    main()
