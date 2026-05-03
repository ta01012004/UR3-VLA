#!/usr/bin/env python3
"""Collect RLBench live demos into a VLA-style imitation dataset.

The dataset is intentionally simple and portable:
  dataset_root/
    manifest.json
    episodes.jsonl
    steps.jsonl
    train.jsonl
    val.jsonl
    episodes/<task>/episode_000000/
      frames/front_rgb/000000.jpg
      trajectory.jsonl

Each step has image paths, an instruction, robot state, and an action label
derived from the next observation. This is enough to train an initial
vision-language-action action head before moving to a larger VLA stack.
"""
import argparse
import json
import os
import random
from pathlib import Path

import numpy as np
from PIL import Image

from rlbench.action_modes.action_mode import MoveArmThenGripper
from rlbench.action_modes.arm_action_modes import JointVelocity
from rlbench.action_modes.gripper_action_modes import Discrete
from rlbench.backend.utils import task_file_to_task_class
from rlbench.environment import Environment
from rlbench.observation_config import ObservationConfig

from rlbench_ur3_support import enable_ur3_robot_setup


_MAX_DEMO_ATTEMPTS = 10


def _to_uint8_rgb(arr):
    arr = np.asarray(arr)
    if arr.dtype != np.uint8:
        if arr.max() <= 1.0:
            arr = arr * 255.0
        arr = np.clip(arr, 0, 255).astype(np.uint8)
    if arr.ndim == 2:
        arr = np.stack([arr, arr, arr], axis=-1)
    return arr[:, :, :3]


def _jsonable(value):
    if value is None:
        return None
    return np.asarray(value).tolist()


def _obs_state(obs):
    return {
        "joint_positions": _jsonable(obs.joint_positions),
        "joint_velocities": _jsonable(obs.joint_velocities),
        "gripper_open": None if obs.gripper_open is None else float(obs.gripper_open),
        "gripper_pose": _jsonable(obs.gripper_pose),
        "task_low_dim_state": _jsonable(obs.task_low_dim_state),
    }


def _action_from_next_obs(obs, next_obs):
    pose = np.asarray(obs.gripper_pose, dtype=np.float32)
    next_pose = np.asarray(next_obs.gripper_pose, dtype=np.float32)
    next_gripper_open = 0.0 if next_obs.gripper_open is None else float(next_obs.gripper_open)
    delta_xyz = next_pose[:3] - pose[:3]

    # Action vector: delta end-effector translation, absolute next quaternion,
    # next gripper open flag. This avoids brittle quaternion-delta math while
    # giving a small, trainable 8D action target.
    action = np.concatenate([
        delta_xyz,
        next_pose[3:7],
        np.asarray([next_gripper_open], dtype=np.float32),
    ]).astype(np.float32)

    return {
        "type": "delta_xyz_abs_quat_gripper",
        "vector": action.tolist(),
        "delta_xyz": delta_xyz.tolist(),
        "target_gripper_pose": next_pose.tolist(),
        "target_gripper_open": next_gripper_open,
    }


def _make_obs_config(cameras):
    obs_config = ObservationConfig()
    obs_config.set_all(False)
    for camera in cameras:
        getattr(obs_config, camera.replace("_rgb", "_camera")).rgb = True
    obs_config.joint_positions = True
    obs_config.joint_velocities = True
    obs_config.gripper_open = True
    obs_config.gripper_pose = True
    obs_config.task_low_dim_state = True
    return obs_config


def _collect_live_demo(task, scene_seed=None):
    ctr_loop = task._robot.arm.joints[0].is_control_loop_enabled()
    task._robot.arm.set_control_loop_enabled(True)
    try:
        attempts = _MAX_DEMO_ATTEMPTS
        last_exc = None
        while attempts > 0:
            if scene_seed is not None:
                np.random.seed(scene_seed)
            random_seed = np.random.get_state()
            descriptions, _ = task.reset()
            try:
                demo = task._scene.get_demo()
                demo.random_seed = random_seed
                return demo, descriptions
            except Exception as exc:
                last_exc = exc
                attempts -= 1
        raise RuntimeError(f"Could not collect live demo: {last_exc!r}")
    finally:
        task._robot.arm.set_control_loop_enabled(ctr_loop)


def _write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="datasets/rlbench_vla")
    parser.add_argument("--tasks", default="slide_block_to_target",
                        help="Comma-separated RLBench task module names")
    parser.add_argument("--episodes-per-task", type=int, default=10)
    parser.add_argument("--variation", type=int, default=0)
    parser.add_argument("--robot-setup", default="panda")
    parser.add_argument("--cameras", default="front_rgb",
                        help="Comma-separated camera RGB fields")
    parser.add_argument("--image-format", default="jpg", choices=["jpg", "png"])
    parser.add_argument("--jpeg-quality", type=int, default=92)
    parser.add_argument("--val-ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--fixed-scene", action="store_true",
                        help="Reuse deterministic scene seeds for debugging")
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    if args.robot_setup.lower() == "ur3":
        ur3_ttm = enable_ur3_robot_setup(os.environ.get("COPPELIASIM_ROOT"))
        print(f"[setup] Enabled experimental UR3 robot setup via {ur3_ttm}")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    tasks = [t.strip() for t in args.tasks.split(",") if t.strip()]
    cameras = [c.strip() for c in args.cameras.split(",") if c.strip()]
    obs_config = _make_obs_config(cameras)
    action_mode = MoveArmThenGripper(
        arm_action_mode=JointVelocity(),
        gripper_action_mode=Discrete(),
    )
    env = Environment(
        action_mode=action_mode,
        obs_config=obs_config,
        headless=True,
        robot_setup=args.robot_setup,
    )

    episodes = []
    steps = []
    global_episode = 0
    global_step = 0

    try:
        env.launch()
        for task_name in tasks:
            task_class = task_file_to_task_class(task_name)
            task = env.get_task(task_class)
            task.set_variation(args.variation)

            for local_episode in range(args.episodes_per_task):
                scene_seed = args.seed + global_episode if args.fixed_scene else None
                print(f"[collect] task={task_name} episode={local_episode + 1}/{args.episodes_per_task}")
                observations, descriptions = _collect_live_demo(task, scene_seed=scene_seed)
                instruction = descriptions[0] if descriptions else task_name.replace("_", " ")

                episode_id = f"{task_name}_{global_episode:06d}"
                episode_dir = out_dir / "episodes" / task_name / f"episode_{global_episode:06d}"
                episode_dir.mkdir(parents=True, exist_ok=True)

                episode_rows = []
                for step_idx in range(max(0, len(observations) - 1)):
                    obs = observations[step_idx]
                    next_obs = observations[step_idx + 1]
                    image_paths = {}

                    for camera in cameras:
                        frame_dir = episode_dir / "frames" / camera
                        frame_dir.mkdir(parents=True, exist_ok=True)
                        suffix = "jpg" if args.image_format == "jpg" else "png"
                        image_path = frame_dir / f"{step_idx:06d}.{suffix}"
                        image = Image.fromarray(_to_uint8_rgb(getattr(obs, camera)))
                        if args.image_format == "jpg":
                            image.save(image_path, quality=args.jpeg_quality)
                        else:
                            image.save(image_path)
                        image_paths[camera] = str(image_path.relative_to(out_dir))

                    row = {
                        "dataset": "rlbench_vla",
                        "task": task_name,
                        "variation": args.variation,
                        "episode_id": episode_id,
                        "episode_index": global_episode,
                        "step_index": step_idx,
                        "global_step": global_step,
                        "instruction": instruction,
                        "descriptions": list(descriptions),
                        "robot_setup": args.robot_setup,
                        "cameras": image_paths,
                        "state": _obs_state(obs),
                        "action": _action_from_next_obs(obs, next_obs),
                    }
                    steps.append(row)
                    episode_rows.append(row)
                    global_step += 1

                _write_jsonl(episode_dir / "trajectory.jsonl", episode_rows)
                episodes.append({
                    "episode_id": episode_id,
                    "task": task_name,
                    "variation": args.variation,
                    "episode_index": global_episode,
                    "num_observations": len(observations),
                    "num_steps": len(episode_rows),
                    "instruction": instruction,
                    "descriptions": list(descriptions),
                    "scene_seed": scene_seed,
                    "trajectory": str((episode_dir / "trajectory.jsonl").relative_to(out_dir)),
                })
                global_episode += 1
    finally:
        env.shutdown()

    episode_indices = list(range(len(episodes)))
    random.shuffle(episode_indices)
    val_count = max(1, int(round(len(episode_indices) * args.val_ratio))) if episodes else 0
    val_episode_indices = set(episode_indices[:val_count])
    train_rows = [s for s in steps if s["episode_index"] not in val_episode_indices]
    val_rows = [s for s in steps if s["episode_index"] in val_episode_indices]

    _write_jsonl(out_dir / "episodes.jsonl", episodes)
    _write_jsonl(out_dir / "steps.jsonl", steps)
    _write_jsonl(out_dir / "train.jsonl", train_rows)
    _write_jsonl(out_dir / "val.jsonl", val_rows)

    manifest = {
        "name": "rlbench_vla",
        "format_version": 1,
        "tasks": tasks,
        "robot_setup": args.robot_setup,
        "cameras": cameras,
        "action_type": "delta_xyz_abs_quat_gripper",
        "num_episodes": len(episodes),
        "num_steps": len(steps),
        "train_steps": len(train_rows),
        "val_steps": len(val_rows),
        "files": {
            "episodes": "episodes.jsonl",
            "steps": "steps.jsonl",
            "train": "train.jsonl",
            "val": "val.jsonl",
        },
    }
    with open(out_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"[ok] Dataset: {out_dir}")
    print(f"[ok] Episodes: {len(episodes)}")
    print(f"[ok] Steps: {len(steps)}")
    print(f"[ok] Train/val: {len(train_rows)}/{len(val_rows)}")


if __name__ == "__main__":
    main()
