#!/usr/bin/env python3
"""Convert existing run_rlbench_video outputs into a VLA-style dataset.

This is useful when the HPC queue is busy but previous RLBench simulation runs
already produced frames and metadata. Actions are derived as:
  [delta_joint_positions(7), next_gripper_open]

The result is still simulation data and currently Panda-based, but it gives a
real trainable dataset immediately.
"""
import argparse
import json
import random
import shutil
from pathlib import Path


def _read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _episode_groups(metadata):
    if "episodes" in metadata and metadata["episodes"]:
        groups = []
        for ep in metadata["episodes"]:
            frames = ep.get("frames", [])
            if frames:
                groups.append((ep.get("episode", len(groups)), frames, ep.get("descriptions") or metadata.get("descriptions") or []))
        return groups

    frames_by_episode = {}
    for frame in metadata.get("frames", []):
        frames_by_episode.setdefault(frame.get("episode", 0), []).append(frame)
    return [
        (episode, sorted(frames, key=lambda x: x.get("step", 0)), metadata.get("descriptions") or [])
        for episode, frames in sorted(frames_by_episode.items())
    ]


def _action_from_next_frame(frame, next_frame):
    q = frame.get("joint_positions")
    next_q = next_frame.get("joint_positions")
    if q is None or next_q is None:
        return None
    delta_q = [float(b) - float(a) for a, b in zip(q, next_q)]
    next_gripper_open = 0.0 if next_frame.get("gripper_open") is None else float(next_frame["gripper_open"])
    return {
        "type": "delta_joint_positions_gripper",
        "vector": delta_q + [next_gripper_open],
        "delta_joint_positions": delta_q,
        "target_gripper_open": next_gripper_open,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--outputs", nargs="+", required=True,
                        help="Output directories containing metadata.json and frames")
    parser.add_argument("--out", default="datasets/rlbench_vla_from_videos")
    parser.add_argument("--val-ratio", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=123)
    args = parser.parse_args()

    random.seed(args.seed)
    out_dir = Path(args.out)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    episodes = []
    steps = []
    global_episode = 0
    global_step = 0

    for output_dir in [Path(p) for p in args.outputs]:
        metadata_path = output_dir / "metadata.json"
        if not metadata_path.exists():
            print(f"[warn] Skipping missing metadata: {metadata_path}")
            continue
        metadata = _read_json(metadata_path)
        task = metadata.get("task") or output_dir.name
        task_key = task.replace(" ", "_").lower()
        instruction = (metadata.get("descriptions") or [task_key])[0]
        robot_setup = metadata.get("robot_setup", "unknown")

        for source_episode, frames, descriptions in _episode_groups(metadata):
            if len(frames) < 2:
                continue
            episode_id = f"{task_key}_{global_episode:06d}"
            episode_dir = out_dir / "episodes" / task_key / f"episode_{global_episode:06d}"
            frame_dir = episode_dir / "frames" / "front_rgb"
            frame_dir.mkdir(parents=True, exist_ok=True)

            episode_rows = []
            for step_idx in range(len(frames) - 1):
                frame = frames[step_idx]
                next_frame = frames[step_idx + 1]
                action = _action_from_next_frame(frame, next_frame)
                if action is None:
                    continue

                src_image = Path(frame["file"])
                if not src_image.is_absolute() and not src_image.exists():
                    src_image = output_dir.parent / src_image
                if not src_image.exists():
                    src_image = output_dir / "frames" / f"frame_{step_idx:05d}.png"
                dst_image = frame_dir / f"{step_idx:06d}.png"
                shutil.copyfile(src_image, dst_image)

                row = {
                    "dataset": "rlbench_vla_from_videos",
                    "task": task_key,
                    "source_output": str(output_dir),
                    "source_episode": source_episode,
                    "episode_id": episode_id,
                    "episode_index": global_episode,
                    "step_index": step_idx,
                    "global_step": global_step,
                    "instruction": instruction,
                    "descriptions": descriptions or metadata.get("descriptions") or [],
                    "robot_setup": robot_setup,
                    "cameras": {
                        "front_rgb": str(dst_image.relative_to(out_dir)),
                    },
                    "state": {
                        "joint_positions": frame.get("joint_positions"),
                        "gripper_open": frame.get("gripper_open"),
                    },
                    "action": action,
                }
                episode_rows.append(row)
                steps.append(row)
                global_step += 1

            _write_jsonl(episode_dir / "trajectory.jsonl", episode_rows)
            episodes.append({
                "episode_id": episode_id,
                "task": task_key,
                "source_output": str(output_dir),
                "source_episode": source_episode,
                "episode_index": global_episode,
                "num_steps": len(episode_rows),
                "instruction": instruction,
                "trajectory": str((episode_dir / "trajectory.jsonl").relative_to(out_dir)),
            })
            global_episode += 1

    indices = list(range(len(episodes)))
    random.shuffle(indices)
    val_count = max(1, round(len(indices) * args.val_ratio)) if episodes else 0
    val_episodes = set(indices[:val_count])
    train_rows = [s for s in steps if s["episode_index"] not in val_episodes]
    val_rows = [s for s in steps if s["episode_index"] in val_episodes]

    _write_jsonl(out_dir / "episodes.jsonl", episodes)
    _write_jsonl(out_dir / "steps.jsonl", steps)
    _write_jsonl(out_dir / "train.jsonl", train_rows)
    _write_jsonl(out_dir / "val.jsonl", val_rows)
    with open(out_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump({
            "name": "rlbench_vla_from_videos",
            "format_version": 1,
            "action_type": "delta_joint_positions_gripper",
            "num_episodes": len(episodes),
            "num_steps": len(steps),
            "train_steps": len(train_rows),
            "val_steps": len(val_rows),
            "source_outputs": args.outputs,
            "files": {
                "episodes": "episodes.jsonl",
                "steps": "steps.jsonl",
                "train": "train.jsonl",
                "val": "val.jsonl",
            },
        }, f, indent=2, ensure_ascii=False)

    print(f"[ok] Dataset: {out_dir}")
    print(f"[ok] Episodes: {len(episodes)}")
    print(f"[ok] Steps: {len(steps)}")
    print(f"[ok] Train/val: {len(train_rows)}/{len(val_rows)}")


if __name__ == "__main__":
    main()
