"""Consolidate finetune experiment metrics into a single CSV."""

import csv
import json
import os
from pathlib import Path

ARTIFACTS = Path(r"C:\Users\ylchen\workspace\research_group\artifacts")
OUTPUT = ARTIFACTS / "experiment_metrics.csv"

CHECKPOINT_ROOTS = [
    (ARTIFACTS / "finetune_checkpoints", "finetune_checkpoints"),
    (ARTIFACTS / "gemini-2.5-pro" / "finetune_us" / "checkpoints", "gemini-2.5-pro"),
]

COLUMNS = [
    "experiment", "group", "val_mse", "best_epoch", "epochs_trained",
    "lr", "batch_size", "epochs_target", "freeze_layers", "max_context",
    "horizon", "stride", "optimizer", "weight_decay", "accumulation_steps",
    "seed", "tickers_or_data", "model_id", "notes",
]


def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


def best_from_lightning(exp_dir):
    """Extract best val_loss from lightning metrics.csv if present."""
    metrics_path = exp_dir / "lightning_logs" / "version_0" / "metrics.csv"
    if not metrics_path.exists():
        return None, None
    best_val = None
    best_epoch = None
    epochs_trained = 0
    try:
        with open(metrics_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("val_loss"):
                    val = float(row["val_loss"])
                    ep = int(row.get("epoch", 0))
                    epochs_trained = max(epochs_trained, ep + 1)
                    if best_val is None or val < best_val:
                        best_val = val
                        best_epoch = ep
    except Exception:
        pass
    return best_val, best_epoch


def parse_checkpoint_dir(exp_dir, group):
    name = exp_dir.name
    args = load_json(exp_dir / "args.json")
    fvm = load_json(exp_dir / "final_val_metric.json")
    history_raw = load_json(exp_dir / "history.json")

    # val_mse
    val_mse = fvm.get("best_val_metric")
    best_epoch = None
    epochs_trained = None

    # Try history.json for best epoch and epoch count
    history = history_raw.get("value", history_raw) if isinstance(history_raw, dict) else history_raw
    if isinstance(history, list) and history:
        epochs_trained = len(history)
        best_ep_data = min(history, key=lambda r: r.get("val_mse", float("inf")))
        best_epoch = best_ep_data.get("epoch")
        if val_mse is None:
            val_mse = best_ep_data.get("val_mse")

    # Fall back to lightning metrics.csv for old-style runs
    if val_mse is None:
        val_mse, best_epoch = best_from_lightning(exp_dir)

    if args is None:
        args = {}

    # Normalize fields across both arg schemas
    lr = args.get("lr") or args.get("learning_rate")
    epochs_target = args.get("epochs") or args.get("max_epochs")
    optimizer = args.get("optimizer", "adamw")
    weight_decay = args.get("weight_decay")
    accumulation_steps = args.get("accumulation_steps")
    freeze_layers = args.get("freeze_layers")
    max_context = args.get("max_context")
    horizon = args.get("horizon")
    stride = args.get("stride")
    seed = args.get("seed")
    batch_size = args.get("batch_size")
    model_id = args.get("model_id") or args.get("model_path", "")
    # Shorten model_id to just the last component for readability
    if model_id:
        model_id = model_id.replace("\\", "/").rstrip("/").split("/")[-1]

    tickers = args.get("tickers") or args.get("data_path") or ""

    # Notes: flag if model is the finetuned exp_11 base
    notes = ""
    if "exp_11" in str(model_id) or "timesfm_finetuning" in str(args.get("model_id", "")):
        notes = "starts from exp_11"
    if not args:
        notes = "no args.json"

    return {
        "experiment": name,
        "group": group,
        "val_mse": f"{val_mse:.8f}" if val_mse is not None else "",
        "best_epoch": best_epoch if best_epoch is not None else "",
        "epochs_trained": epochs_trained if epochs_trained is not None else "",
        "lr": lr if lr is not None else "",
        "batch_size": batch_size if batch_size is not None else "",
        "epochs_target": epochs_target if epochs_target is not None else "",
        "freeze_layers": freeze_layers if freeze_layers is not None else "",
        "max_context": max_context if max_context is not None else "",
        "horizon": horizon if horizon is not None else "",
        "stride": stride if stride is not None else "",
        "optimizer": optimizer if optimizer is not None else "",
        "weight_decay": weight_decay if weight_decay is not None else "",
        "accumulation_steps": accumulation_steps if accumulation_steps is not None else "",
        "seed": seed if seed is not None else "",
        "tickers_or_data": tickers,
        "model_id": model_id,
        "notes": notes,
    }


rows = []
for root, group in CHECKPOINT_ROOTS:
    if not root.exists():
        continue
    for exp_dir in sorted(root.iterdir()):
        if not exp_dir.is_dir():
            continue
        row = parse_checkpoint_dir(exp_dir, group)
        rows.append(row)

# Sort by val_mse ascending (empty/None last)
rows.sort(key=lambda r: (r["val_mse"] == "", float(r["val_mse"]) if r["val_mse"] else float("inf")))

with open(OUTPUT, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerows(rows)

print(f"Written {len(rows)} experiments to {OUTPUT}")
for r in rows:
    tag = f"  val_mse={r['val_mse']}" if r["val_mse"] else "  val_mse=N/A"
    print(f"  {r['group']}/{r['experiment']}{tag}")
