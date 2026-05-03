#!/usr/bin/env python3
"""Train a small vision-language-action action head on exported RLBench data.

This is a baseline trainer, not a full foundation VLA. It proves that the
collected dataset is trainable: image + instruction -> 8D action vector.
The saved checkpoint can be replaced later by OpenVLA/RT-1/OpenPI fine-tuning.
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset


def _read_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _tokens(text):
    return re.findall(r"[a-z0-9_]+", text.lower())


def _build_vocab(rows, max_words=2048):
    counts = Counter()
    for row in rows:
        counts.update(_tokens(row["instruction"]))
    vocab = {"<pad>": 0, "<unk>": 1}
    for word, _ in counts.most_common(max_words - len(vocab)):
        vocab[word] = len(vocab)
    return vocab


def _encode_text(text, vocab, max_len):
    ids = [vocab.get(tok, vocab["<unk>"]) for tok in _tokens(text)[:max_len]]
    ids += [0] * (max_len - len(ids))
    return torch.tensor(ids, dtype=torch.long)


class RlbenchVlaDataset(Dataset):
    def __init__(self, dataset_root, split, vocab=None, max_text_len=32, image_size=128):
        self.root = Path(dataset_root)
        self.rows = _read_jsonl(self.root / f"{split}.jsonl")
        self.vocab = vocab or _build_vocab(self.rows)
        self.max_text_len = max_text_len
        self.image_size = image_size

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, idx):
        row = self.rows[idx]
        image_rel = row["cameras"].get("front_rgb") or next(iter(row["cameras"].values()))
        image = Image.open(self.root / image_rel).convert("RGB").resize((self.image_size, self.image_size))
        image_arr = np.asarray(image, dtype=np.float32) / 255.0
        image_tensor = torch.from_numpy(image_arr).permute(2, 0, 1)
        text = _encode_text(row["instruction"], self.vocab, self.max_text_len)
        action = torch.tensor(row["action"]["vector"], dtype=torch.float32)
        return image_tensor, text, action


class TinyVlaActionHead(nn.Module):
    def __init__(self, vocab_size, action_dim=8):
        super().__init__()
        self.image_encoder = nn.Sequential(
            nn.Conv2d(3, 32, 5, stride=2, padding=2),
            nn.ReLU(inplace=True),
            nn.Conv2d(32, 64, 5, stride=2, padding=2),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 128, 3, stride=2, padding=1),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((1, 1)),
            nn.Flatten(),
        )
        self.text_embedding = nn.Embedding(vocab_size, 64, padding_idx=0)
        self.head = nn.Sequential(
            nn.Linear(128 + 64, 256),
            nn.ReLU(inplace=True),
            nn.Linear(256, 128),
            nn.ReLU(inplace=True),
            nn.Linear(128, action_dim),
        )

    def forward(self, image, text):
        image_features = self.image_encoder(image)
        text_emb = self.text_embedding(text)
        mask = (text != 0).float().unsqueeze(-1)
        text_features = (text_emb * mask).sum(dim=1) / mask.sum(dim=1).clamp_min(1.0)
        return self.head(torch.cat([image_features, text_features], dim=1))


def _evaluate(model, loader, device):
    model.eval()
    loss_fn = nn.MSELoss(reduction="sum")
    total_loss = 0.0
    total = 0
    with torch.no_grad():
        for image, text, action in loader:
            image = image.to(device)
            text = text.to(device)
            action = action.to(device)
            pred = model(image, text)
            total_loss += loss_fn(pred, action).item()
            total += action.numel()
    return total_loss / max(1, total)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="datasets/rlbench_vla")
    parser.add_argument("--out", default="checkpoints/tiny_vla_action_head.pt")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--image-size", type=int, default=128)
    parser.add_argument("--max-text-len", type=int, default=32)
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    train_ds = RlbenchVlaDataset(args.dataset, "train", image_size=args.image_size, max_text_len=args.max_text_len)
    val_ds = RlbenchVlaDataset(args.dataset, "val", vocab=train_ds.vocab, image_size=args.image_size, max_text_len=args.max_text_len)
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=2)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=2)

    model = TinyVlaActionHead(vocab_size=len(train_ds.vocab)).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr)
    loss_fn = nn.MSELoss()

    for epoch in range(args.epochs):
        model.train()
        total_loss = 0.0
        total_batches = 0
        for image, text, action in train_loader:
            image = image.to(device)
            text = text.to(device)
            action = action.to(device)
            pred = model(image, text)
            loss = loss_fn(pred, action)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            total_loss += loss.item()
            total_batches += 1
        train_loss = total_loss / max(1, total_batches)
        val_loss = _evaluate(model, val_loader, device)
        print(f"[epoch {epoch + 1}/{args.epochs}] train_mse={train_loss:.6f} val_mse={val_loss:.6f}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "model_state": model.state_dict(),
        "vocab": train_ds.vocab,
        "action_type": "delta_xyz_abs_quat_gripper",
        "image_size": args.image_size,
        "max_text_len": args.max_text_len,
    }, out_path)
    print(f"[ok] Saved checkpoint: {out_path}")


if __name__ == "__main__":
    main()
