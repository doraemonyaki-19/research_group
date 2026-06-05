"""Aggregate Phase 3 ablation results into a per-cell DataFrame + figures.

Inputs:  results/{config}/{region}/seed_{N}_*/run_data.json
Outputs:
  - benchmarks/results_aggregate.csv     — one row per run
  - benchmarks/results_per_cell.csv      — one row per (config, region, seed); means + SE
  - benchmarks/figures/cost_per_config.png
  - benchmarks/figures/turns_per_config.png
  - benchmarks/figures/tokens_per_config.png
  - benchmarks/figures/best_result_per_config.png  (only if best_result extractor is registered)

Best-result extraction is task-specific. The protocol's primary metric for T1 (TimesFM)
is "lowest 120d MAPE on held-out". That number is buried in agent free-text and requires
a task-specific parser. Register one via `--task-extractor` (see EXTRACTORS dict below).
For now, T1 ships with a `timesfm_120d_mape` extractor that scans turn_history for
the smallest "120d ... X.XXpp"-style number.

Run from repo root:
    python benchmarks/aggregate_results.py
    python benchmarks/aggregate_results.py --task-extractor timesfm_120d_mape
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from statistics import mean, stdev

import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_ROOT = REPO_ROOT / "results"
BENCH_DIR = REPO_ROOT / "benchmarks"
FIG_DIR = BENCH_DIR / "figures"


# =============================================================================
# Task-specific best-result extractors
# =============================================================================
# Each extractor takes a run_data dict and returns a float (best result value)
# or None if no value could be extracted. Lower-is-better is task-specific —
# the aggregator just records the value; the figure caption explains direction.

_MAPE_120D_PATTERN = re.compile(
    r"120d[^0-9\-]{0,30}([\-\+]?\d+(?:\.\d+)?)\s*(?:pp|%)?",
    re.IGNORECASE,
)


def _timesfm_120d_mape(run_data: dict) -> float | None:
    """Extract the lowest reported 120d MAPE from agent turn outputs.

    Heuristic — scans every turn output for "120d ... <number> [pp|%]" and
    returns the minimum. Brittle to phrasing changes; use as a starting point
    for T1, not as a final-paper artifact.
    """
    candidates: list[float] = []
    for turn in run_data.get("turn_history", []):
        text = turn.get("output", "") or ""
        for match in _MAPE_120D_PATTERN.finditer(text):
            try:
                v = float(match.group(1))
                # Skip implausible values (negative pp deltas, gigantic numbers)
                if 0.5 <= v <= 100.0:
                    candidates.append(v)
            except ValueError:
                continue
    return min(candidates) if candidates else None


EXTRACTORS = {
    "timesfm_120d_mape": _timesfm_120d_mape,
}


# =============================================================================
# Loading + flattening
# =============================================================================


def load_runs(extractor_name: str | None = None) -> pd.DataFrame:
    """Find all run_data.json files and return a flat per-run DataFrame."""
    extractor = EXTRACTORS.get(extractor_name) if extractor_name else None
    rows: list[dict] = []

    paths = list(RESULTS_ROOT.glob("*/*/seed_*/run_data.json")) + list(RESULTS_ROOT.glob("*/*/*/seed_*/run_data.json"))
    for run_data_path in paths:
        try:
            with open(run_data_path, encoding="utf-8") as f:
                rd = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"WARN: skipping {run_data_path}: {e}")
            continue

        meta = rd.get("metadata", {})
        result = rd.get("result", {})

        row = {
            "run_dir": str(run_data_path.parent.relative_to(REPO_ROOT)),
            "config": meta.get("config") or run_data_path.parent.parent.parent.name,
            "region": meta.get("region") or run_data_path.parent.parent.name,
            "seed": meta.get("seed"),
            "loop_class": meta.get("loop_class"),
            "model": meta.get("model"),
            "max_turns": meta.get("max_turns"),
            "started_at": meta.get("started_at"),
            "completed_at": meta.get("completed_at"),
            "stop_reason": result.get("stop_reason"),
            "turns_completed": result.get("turns_completed"),
            "directions_killed": result.get("directions_killed", 0),
            "directions_explored": result.get("directions_explored", 0),
            "input_tokens": result.get("total_input_tokens", 0),
            "output_tokens": result.get("total_output_tokens", 0),
            "cost_usd": result.get("estimated_cost_usd", 0.0),
        }

        # Fallback for legacy layouts where seed wasn't in metadata
        if row["seed"] is None:
            m = re.match(r"seed_(\d+)_", run_data_path.parent.name)
            if m:
                row["seed"] = int(m.group(1))

        if extractor is not None:
            row["best_result"] = extractor(rd)
        else:
            row["best_result"] = None

        rows.append(row)

    if not rows:
        raise SystemExit(
            f"No run_data.json files found under {RESULTS_ROOT}. "
            "Expected layout: results/{config}/{region}/seed_*/run_data.json"
        )

    return pd.DataFrame(rows).sort_values(["config", "region", "seed"]).reset_index(drop=True)


# =============================================================================
# Per-cell aggregation
# =============================================================================


def per_cell_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate to one row per (config, region) — means and SE across seeds."""
    rows = []
    for (config, region), grp in df.groupby(["config", "region"], sort=False):
        n = len(grp)
        row = {"config": config, "region": region, "n_seeds": n}

        for col in ["turns_completed", "input_tokens", "output_tokens", "cost_usd", "best_result"]:
            vals = [v for v in grp[col].tolist() if v is not None and not pd.isna(v)]
            if not vals:
                row[f"{col}_mean"] = None
                row[f"{col}_se"] = None
                continue
            row[f"{col}_mean"] = mean(vals)
            row[f"{col}_se"] = stdev(vals) / (len(vals) ** 0.5) if len(vals) > 1 else 0.0

        # Stop-reason distribution
        for sr in ["max_turns", "done", "terminate", "approved", "error"]:
            row[f"stop_{sr}"] = int((grp["stop_reason"] == sr).sum())

        rows.append(row)
    return pd.DataFrame(rows)


# =============================================================================
# Plots
# =============================================================================


def _config_order(df: pd.DataFrame) -> list[str]:
    """Stable left-to-right ordering: B2, V1, V2-Full, then anything else."""
    canonical = ["B2", "V1", "V2-Full", "V2-noSkills"]
    seen = list(df["config"].unique())
    return [c for c in canonical if c in seen] + [c for c in seen if c not in canonical]


def _box_with_jitter(ax, df: pd.DataFrame, value_col: str, ylabel: str, title: str) -> None:
    configs = _config_order(df)
    data = [df.loc[df["config"] == c, value_col].dropna().tolist() for c in configs]
    bp = ax.boxplot(data, labels=configs, showmeans=True, meanline=True, widths=0.5)
    # Overlay individual points
    for i, vals in enumerate(data, start=1):
        if vals:
            jitter = [i + (j - len(vals) / 2) * 0.05 for j in range(len(vals))]
            ax.scatter(jitter, vals, alpha=0.5, s=24, color="#1f77b4", zorder=3)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.3)
    # Annotate n_seeds per config
    for i, _c in enumerate(configs, start=1):
        n = len(data[i - 1])
        ax.annotate(f"n={n}", xy=(i, ax.get_ylim()[0]), xytext=(0, -18),
                    textcoords="offset points", ha="center", fontsize=8, color="dimgray")
    return bp


def plot_all(df: pd.DataFrame, fig_dir: Path) -> list[Path]:
    fig_dir.mkdir(parents=True, exist_ok=True)
    written = []

    # Figure 1: Cost per config
    fig, ax = plt.subplots(figsize=(7, 4.5))
    _box_with_jitter(ax, df, "cost_usd", "Estimated cost per run (USD)", "Cost per config")
    fig.tight_layout()
    p = fig_dir / "cost_per_config.png"
    fig.savefig(p, dpi=140)
    plt.close(fig)
    written.append(p)

    # Figure 2: Turns completed
    fig, ax = plt.subplots(figsize=(7, 4.5))
    _box_with_jitter(ax, df, "turns_completed", "Turns completed", "Turns to termination per config")
    fig.tight_layout()
    p = fig_dir / "turns_per_config.png"
    fig.savefig(p, dpi=140)
    plt.close(fig)
    written.append(p)

    # Figure 3: Tokens (input+output stacked)
    configs = _config_order(df)
    in_means = [df.loc[df["config"] == c, "input_tokens"].mean() for c in configs]
    out_means = [df.loc[df["config"] == c, "output_tokens"].mean() for c in configs]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    x = range(len(configs))
    ax.bar(x, in_means, label="Input tokens (mean)", color="#1f77b4")
    ax.bar(x, out_means, bottom=in_means, label="Output tokens (mean)", color="#ff7f0e")
    ax.set_xticks(list(x))
    ax.set_xticklabels(configs)
    ax.set_ylabel("Tokens (mean across seeds)")
    ax.set_title("Token footprint per config")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    p = fig_dir / "tokens_per_config.png"
    fig.savefig(p, dpi=140)
    plt.close(fig)
    written.append(p)

    # Figure 4: best_result if extracted
    if "best_result" in df.columns and df["best_result"].notna().any():
        fig, ax = plt.subplots(figsize=(7, 4.5))
        _box_with_jitter(ax, df, "best_result", "Best result (task-specific; lower is better for MAPE)",
                         "Best result per config")
        fig.tight_layout()
        p = fig_dir / "best_result_per_config.png"
        fig.savefig(p, dpi=140)
    plt.close(fig)
    written.append(p)

    return written


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(description="Aggregate ResearchGroup ablation results.")
    parser.add_argument(
        "--task-extractor",
        choices=sorted(EXTRACTORS.keys()),
        help="Task-specific extractor for the 'best_result' column.",
    )
    parser.add_argument("--no-plots", action="store_true", help="Skip plot generation.")
    args = parser.parse_args()

    df = load_runs(args.task_extractor)
    print(f"Loaded {len(df)} runs across {df['config'].nunique()} configs.")
    print(df[["config", "region", "seed", "stop_reason", "turns_completed", "cost_usd"]])

    out_csv = BENCH_DIR / "results_aggregate.csv"
    df.to_csv(out_csv, index=False)
    print(f"\nWrote {out_csv}")

    cell_df = per_cell_summary(df)
    out_cell = BENCH_DIR / "results_per_cell.csv"
    cell_df.to_csv(out_cell, index=False)
    print(f"Wrote {out_cell}")
    print("\nPer-cell summary:")
    with pd.option_context("display.width", 200, "display.max_columns", None):
        print(cell_df)

    if not args.no_plots:
        written = plot_all(df, FIG_DIR)
        print("\nFigures:")
        for p in written:
            print(f"  {p.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
