#!/usr/bin/env python3
"""Convert the local RLBench VLA JSONL dataset into LeRobotDataset format.

This prepares data for policies such as SmolVLA.  It does not upload anything
to Hugging Face Hub; the resulting dataset stays local under HF_LEROBOT_HOME.
"""
import argparse
import json
import os
import shutil
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image


def _read_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _camera_name(camera_key):
    return camera_key[:-4] if camera_key.endswith("_rgb") else camera_key


def _load_image(path, image_size=None):
    image = Image.open(path).convert("RGB")
    if image_size is not None:
        image = image.resize((image_size, image_size))
    return np.asarray(image, dtype=np.uint8)


def _state_vector(row):
    state = row["state"]
    joint_positions = state.get("joint_positions") or []
    gripper_pose = state.get("gripper_pose") or []
    gripper_open = state.get("gripper_open")
    if gripper_open is None:
        gripper_open = 0.0
    return np.asarray([*joint_positions, *gripper_pose, gripper_open], dtype=np.float32)


def _action_vector(row):
    return np.asarray(row["action"]["vector"], dtype=np.float32)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", default="datasets/rlbench_vla_slide_100ep")
    parser.add_argument("--repo-id", default="ta01012004/rlbench_slide_block_to_target_100ep")
    parser.add_argument("--hf-lerobot-home", default="datasets/lerobot_cache")
    parser.add_argument("--split", default="steps", choices=["steps", "train", "val"])
    parser.add_argument("--fps", type=int, default=20)
    parser.add_argument("--image-size", type=int, default=128)
    parser.add_argument("--use-videos", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    from lerobot.datasets.lerobot_dataset import LeRobotDataset

    src = Path(args.src).resolve()
    hf_home = Path(args.hf_lerobot_home).resolve()
    os.environ["HF_LEROBOT_HOME"] = str(hf_home)

    rows = _read_jsonl(src / f"{args.split}.jsonl")
    if not rows:
        raise RuntimeError(f"No rows found in {src / f'{args.split}.jsonl'}")

    first = rows[0]
    camera_keys = list(first["cameras"].keys())
    camera_names = [_camera_name(k) for k in camera_keys]
    sample_image = _load_image(src / first["cameras"][camera_keys[0]], args.image_size)
    state_dim = int(_state_vector(first).shape[0])
    action_dim = int(_action_vector(first).shape[0])

    dataset_root = hf_home / args.repo_id
    if dataset_root.exists() and args.overwrite:
        shutil.rmtree(dataset_root)
    if dataset_root.exists():
        raise RuntimeError(f"LeRobot dataset already exists: {dataset_root}. Use --overwrite to replace it.")

    image_dtype = "video" if args.use_videos else "image"
    features = {
        "observation.state": {
            "dtype": "float32",
            "shape": (state_dim,),
            "names": None,
        },
        "action": {
            "dtype": "float32",
            "shape": (action_dim,),
            "names": None,
        },
    }
    for name in camera_names:
        features[f"observation.images.{name}"] = {
            "dtype": image_dtype,
            "shape": tuple(sample_image.shape),
            "names": ["height", "width", "channel"],
        }

    dataset = LeRobotDataset.create(
        repo_id=args.repo_id,
        fps=args.fps,
        features=features,
        robot_type=first.get("robot_setup", "panda"),
        use_videos=args.use_videos,
    )

    by_episode = defaultdict(list)
    for row in rows:
        by_episode[row["episode_index"]].append(row)

    for episode_index in sorted(by_episode):
        episode_rows = sorted(by_episode[episode_index], key=lambda r: r["step_index"])
        for row in episode_rows:
            frame = {
                "observation.state": _state_vector(row),
                "action": _action_vector(row),
                "task": row["instruction"],
            }
            for camera_key, camera_name in zip(camera_keys, camera_names):
                frame[f"observation.images.{camera_name}"] = _load_image(
                    src / row["cameras"][camera_key],
                    args.image_size,
                )
            dataset.add_frame(frame)
        dataset.save_episode()
        print(f"[convert] saved episode={episode_index} frames={len(episode_rows)}")

    dataset.finalize()
    print(f"[ok] repo_id={args.repo_id}")
    print(f"[ok] root={dataset.root}")
    print(f"[ok] episodes={dataset.num_episodes}")
    print(f"[ok] frames={dataset.num_frames}")


if __name__ == "__main__":
    main()
