#!/usr/bin/env python3
"""Run one RLBench live demonstration headlessly and save frames + mp4.

Default task: PickUpCup (has a visible object). If that task fails on a local
RLBench version, the script falls back to ReachTarget so that the pipeline can
still validate installation/rendering.
"""
import argparse
import json
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image

from rlbench.action_modes.action_mode import MoveArmThenGripper
from rlbench.action_modes.arm_action_modes import JointVelocity
from rlbench.action_modes.gripper_action_modes import Discrete
from rlbench.backend.utils import task_file_to_task_class
from rlbench.environment import Environment
from rlbench.observation_config import ObservationConfig
from rlbench.tasks import ReachTarget


def _to_uint8_rgb(arr):
    arr = np.asarray(arr)
    if arr.dtype != np.uint8:
        if arr.max() <= 1.0:
            arr = arr * 255.0
        arr = np.clip(arr, 0, 255).astype(np.uint8)
    if arr.ndim == 2:
        arr = np.stack([arr, arr, arr], axis=-1)
    return arr[:, :, :3]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="outputs/pick_up_cup_demo", help="Output directory")
    parser.add_argument("--fps", type=int, default=20)
    parser.add_argument("--camera", default="front_rgb", choices=[
        "front_rgb", "left_shoulder_rgb", "right_shoulder_rgb", "wrist_rgb", "overhead_rgb"
    ])
    parser.add_argument("--variation", type=int, default=0)
    parser.add_argument("--task", default="pick_up_cup",
                        help="RLBench task module name, e.g. pick_up_cup, slide_block_to_target")
    parser.add_argument("--robot-setup", default="panda", help="RLBench robot setup; upstream includes panda, ur5, sawyer, mico, jaco")
    args = parser.parse_args()

    out_dir = Path(args.out)
    frame_dir = out_dir / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)

    obs_config = ObservationConfig()
    obs_config.set_all(False)
    getattr(obs_config, args.camera.replace("_rgb", "_camera")).rgb = True
    obs_config.joint_positions = True
    obs_config.joint_velocities = True
    obs_config.gripper_open = True
    obs_config.gripper_pose = True
    obs_config.task_low_dim_state = True

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

    metadata = {
        "task": None,
        "descriptions": None,
        "robot_setup": args.robot_setup,
        "headless": True,
        "camera": args.camera,
        "frames": [],
    }

    try:
        env.launch()
        try:
            task_class = task_file_to_task_class(args.task)
            task = env.get_task(task_class)
            task.set_variation(args.variation)
            demos = task.get_demos(1, live_demos=True)
            metadata["task"] = task_class.__name__
        except Exception as exc:
            print(f"[warn] {args.task} live demo failed: {exc}")
            print("[warn] Falling back to ReachTarget installation smoke test.")
            task = env.get_task(ReachTarget)
            task.set_variation(0)
            demos = task.get_demos(1, live_demos=True)
            metadata["task"] = "ReachTarget"
            metadata["fallback_reason"] = repr(exc)

        descriptions, _ = task.reset()
        metadata["descriptions"] = list(descriptions)

        observations = demos[0]
        frames = []
        for i, obs in enumerate(observations):
            rgb = _to_uint8_rgb(getattr(obs, args.camera))
            frame_path = frame_dir / f"frame_{i:05d}.png"
            Image.fromarray(rgb).save(frame_path)
            frames.append(rgb)
            metadata["frames"].append({
                "step": i,
                "file": str(frame_path),
                "gripper_open": None if obs.gripper_open is None else float(obs.gripper_open),
                "joint_positions": None if obs.joint_positions is None else np.asarray(obs.joint_positions).tolist(),
            })

        video_path = out_dir / "simulation.mp4"
        imageio.mimsave(video_path, frames, fps=args.fps, macro_block_size=1)
        metadata["video"] = str(video_path)
        metadata["num_frames"] = len(frames)
        with open(out_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        print(f"[ok] Saved {len(frames)} frames to {frame_dir}")
        print(f"[ok] Saved video to {video_path}")
    finally:
        env.shutdown()


if __name__ == "__main__":
    main()
