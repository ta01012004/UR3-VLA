#!/usr/bin/env python3
"""Evaluate a trained tiny VLA action head on a dataset split."""
import argparse
from pathlib import Path

import torch
from torch.utils.data import DataLoader

from train_vla_action_head import RlbenchVlaDataset, TinyVlaActionHead


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="datasets/rlbench_vla_from_videos")
    parser.add_argument("--checkpoint", default="checkpoints/tiny_vla_action_head_from_videos.pt")
    parser.add_argument("--split", default="val", choices=["train", "val"])
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--samples", type=int, default=5)
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(args.checkpoint, map_location=device)
    dataset = RlbenchVlaDataset(
        args.dataset,
        args.split,
        vocab=ckpt["vocab"],
        image_size=ckpt.get("image_size", 128),
        max_text_len=ckpt.get("max_text_len", 32),
    )
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=False, num_workers=2)

    model = TinyVlaActionHead(vocab_size=len(ckpt["vocab"])).to(device)
    model.load_state_dict(ckpt["model_state"])
    model.eval()

    total_sq = 0.0
    total_abs = 0.0
    total_items = 0
    sample_rows = []

    with torch.no_grad():
        for image, text, action in loader:
            image = image.to(device)
            text = text.to(device)
            action = action.to(device)
            pred = model(image, text)
            diff = pred - action
            total_sq += diff.pow(2).sum().item()
            total_abs += diff.abs().sum().item()
            total_items += action.numel()
            if len(sample_rows) < args.samples:
                for p, a in zip(pred.cpu(), action.cpu()):
                    sample_rows.append((p.tolist(), a.tolist()))
                    if len(sample_rows) >= args.samples:
                        break

    mse = total_sq / max(1, total_items)
    mae = total_abs / max(1, total_items)
    print(f"[eval] dataset={args.dataset}")
    print(f"[eval] split={args.split}")
    print(f"[eval] samples={len(dataset)}")
    print(f"[eval] action_type={ckpt.get('action_type')}")
    print(f"[eval] mse={mse:.8f}")
    print(f"[eval] mae={mae:.8f}")
    print("[eval] prediction samples: pred -> target")
    for i, (pred, target) in enumerate(sample_rows):
        pred_s = ", ".join(f"{x:.4f}" for x in pred)
        target_s = ", ".join(f"{x:.4f}" for x in target)
        print(f"  {i}: [{pred_s}] -> [{target_s}]")


if __name__ == "__main__":
    main()
