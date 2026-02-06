#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Heatmap generator for new_ttm_details_*.csv (and similar exports)

What it does (per each input CSV):
- Filter: Разработка == 1
- Квартал: empty -> "WiP"
- Builds heatmaps by Команда x Квартал with cell text: "N / value"
- Color scale: RdYlGn_r with "orange from threshold" (TwoSlopeNorm with vcenter=threshold)
- Hatch "///" when value <= threshold
- Saves PNGs

Metrics supported:
1) DevLT: uses rows with DevLT not null
2) Tail: uses rows with Tail > 0
3) TTM_adj = max(0, TTM - Discovery_backlog_column): uses rows with TTM_adj not null

Aggregations supported:
- median
- mean
- p85 (85th percentile)
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import colors
from matplotlib.patches import Rectangle

from radiator.core.logging import logger

# =========================
# CONFIG (defaults)
# =========================

DEFAULT_OUTPUT_DIR: str = "data/heatmaps"
FIGSIZE: Tuple[int, int] = (10, 6)
CMAP: str = "RdYlGn_r"  # green (low) -> red (high)

# Which aggregations to generate for each metric
DEFAULT_AGGS: List[str] = ["median", "p85"]  # or ["median", "mean", "p85"]

# Hatch thresholds
DEFAULT_THRESHOLDS: Dict[str, float] = {
    "DevLT": 60.0,
    "Tail": 60.0,
    "TTM_adj": 180.0,
}

# Visual text style
TEXT_COLOR = "white"
TEXT_SIZE = 12
TEXT_STROKE_WIDTH = 2

# =========================
# END CONFIG
# =========================


def log(msg: str) -> None:
    """Log message using project logger."""
    logger.info(f"[heatmap] {msg}")


def quarter_sort_key(q: str) -> Tuple[int, int, int, str]:
    """Sort quarters like 2025Q4, 2025.Q4, etc; put WiP last."""
    if q == "WiP":
        return (9999, 9, 1, q)
    s = str(q)
    m = re.search(r"(\d{4}).*?[Qq](\d)", s)
    if m:
        return (int(m.group(1)), int(m.group(2)), 0, s)
    return (9998, 9, 0, s)


def find_discovery_backlog_column(cols: List[str]) -> Optional[str]:
    """Find discovery backlog column by name (case-insensitive)."""
    for c in cols:
        cl = c.lower()
        if "discovery" in cl and "backlog" in cl:
            return c
    return None


def agg_func(agg: str) -> Callable[[pd.Series], float]:
    if agg == "median":
        return np.median
    if agg == "mean":
        return np.mean
    if agg == "p85":
        return lambda x: float(np.percentile(x, 85))
    raise ValueError(f"Unknown agg: {agg}")


def build_heatmap(
    df: pd.DataFrame,
    metric_col: str,
    agg: str,
    threshold: float,
    out_path: str,
    filter_mask: pd.Series,
    title: str,
) -> None:
    d = df.loc[filter_mask].copy()
    d[metric_col] = pd.to_numeric(d[metric_col], errors="coerce")
    d = d[~d[metric_col].isna()].copy()

    if d.empty:
        log(f"SKIP {title}: no rows after filters")
        return

    pv = d.pivot_table(
        index="Команда",
        columns="Квартал",
        values=metric_col,
        aggfunc=agg_func(agg),
    )
    cnt = d.pivot_table(
        index="Команда",
        columns="Квартал",
        values=metric_col,
        aggfunc="count",
    )

    cols = sorted(pv.columns.tolist(), key=quarter_sort_key)
    pv = pv.reindex(columns=cols).sort_index()
    cnt = cnt.reindex(index=pv.index, columns=cols)

    vals = pv.to_numpy(dtype=float)

    # "orange from threshold": hinge at vcenter=threshold
    vmax = np.nanmax(vals)
    if not np.isfinite(vmax):
        log(f"SKIP {title}: vmax is not finite")
        return
    if vmax <= threshold:
        vmax = threshold * 1.01

    norm = colors.TwoSlopeNorm(vmin=0, vcenter=threshold, vmax=vmax)

    fig, ax = plt.subplots(figsize=FIGSIZE)
    im = ax.imshow(vals, cmap=CMAP, norm=norm, aspect="auto")

    ax.set_xticks(np.arange(len(cols)))
    ax.set_yticks(np.arange(len(pv.index)))
    ax.set_xticklabels(cols, rotation=45, ha="right")
    ax.set_yticklabels(pv.index)

    # light grid
    ax.set_xticks(np.arange(-0.5, len(cols), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(pv.index), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1)
    ax.tick_params(which="minor", bottom=False, left=False)

    # labels + hatch
    for i in range(vals.shape[0]):
        for j in range(vals.shape[1]):
            v = vals[i, j]
            n = cnt.iloc[i, j]
            if np.isfinite(v) and np.isfinite(n) and n > 0:
                t = ax.text(
                    j,
                    i,
                    f"{int(n)} / {int(round(v))}",
                    ha="center",
                    va="center",
                    color=TEXT_COLOR,
                    fontsize=TEXT_SIZE,
                )
                t.set_path_effects(
                    [
                        pe.Stroke(linewidth=TEXT_STROKE_WIDTH, foreground="black"),
                        pe.Normal(),
                    ]
                )
                if v <= threshold:
                    ax.add_patch(
                        Rectangle(
                            (j - 0.5, i - 0.5),
                            1,
                            1,
                            fill=False,
                            hatch="///",
                            linewidth=0,
                        )
                    )

    ax.set_title(title)
    fig.colorbar(im, ax=ax, label=f"{agg}({metric_col})")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    log(f"saved: {out_path}")


def load_and_prepare(csv_path: str) -> pd.DataFrame:
    log(f"loading: {csv_path}")
    df = pd.read_csv(csv_path)

    required = ["Разработка", "Квартал", "Команда"]
    for c in required:
        if c not in df.columns:
            raise ValueError(f"Missing required column '{c}' in {csv_path}")

    df = df[df["Разработка"] == 1].copy()

    df["Квартал"] = df["Квартал"].astype("string").fillna("").str.strip()
    df.loc[df["Квартал"] == "", "Квартал"] = "WiP"

    # Best-effort: key column for WIP count is used only in other reports,
    # for heatmaps we don't need it. Still nice to have for debugging.
    return df


def generate_for_file(
    csv_path: str, output_dir: str, aggs: List[str], thresholds: Dict[str, float]
) -> None:
    """Generate heatmaps for a single CSV file."""
    df = load_and_prepare(csv_path)

    stem = os.path.splitext(os.path.basename(csv_path))[0]
    out_base = os.path.join(output_dir, stem)

    # Find discovery backlog column for TTM_adj
    disc_col = find_discovery_backlog_column(df.columns.tolist())
    if disc_col is None:
        log("WARN: Discovery backlog column not found (TTM_adj will be skipped).")

    # Prepare TTM_adj if possible
    if "TTM" in df.columns and disc_col is not None:
        df["TTM"] = pd.to_numeric(df["TTM"], errors="coerce")
        disc = pd.to_numeric(df[disc_col], errors="coerce").fillna(0)
        df["TTM_adj"] = (df["TTM"] - disc).clip(lower=0)

    # Masks per metric
    devlt_mask = (
        df["DevLT"].apply(lambda x: pd.notna(pd.to_numeric(x, errors="coerce")))
        if "DevLT" in df.columns
        else None
    )
    tail_mask = (
        (pd.to_numeric(df["Tail"], errors="coerce") > 0)
        if "Tail" in df.columns
        else None
    )
    ttm_adj_mask = df["TTM_adj"].notna() if "TTM_adj" in df.columns else None

    # Generate
    for agg in aggs:
        if devlt_mask is not None:
            build_heatmap(
                df=df,
                metric_col="DevLT",
                agg=agg,
                threshold=thresholds["DevLT"],
                out_path=os.path.join(out_base, f"devlt_{agg}_heatmap.png"),
                filter_mask=devlt_mask,
                title=f"DevLT heatmap ({agg}) | оранжевый от {thresholds['DevLT']} | штриховка: {agg} ≤ {thresholds['DevLT']} | WiP = незавершённые задачи",
            )

        if tail_mask is not None:
            build_heatmap(
                df=df,
                metric_col="Tail",
                agg=agg,
                threshold=thresholds["Tail"],
                out_path=os.path.join(out_base, f"tail_{agg}_heatmap.png"),
                filter_mask=tail_mask,
                title=f"Tail heatmap ({agg}) | оранжевый от {thresholds['Tail']} | штриховка: {agg} ≤ {thresholds['Tail']} | WiP = незавершённые задачи",
            )

        if ttm_adj_mask is not None:
            build_heatmap(
                df=df,
                metric_col="TTM_adj",
                agg=agg,
                threshold=thresholds["TTM_adj"],
                out_path=os.path.join(out_base, f"ttm_adj_{agg}_heatmap.png"),
                filter_mask=ttm_adj_mask,
                title=f"TTM_adj heatmap ({agg}) | оранжевый от {thresholds['TTM_adj']} | штриховка: {agg} ≤ {thresholds['TTM_adj']} | WiP = незавершённые задачи",
            )


def main():
    """Main function for command line execution."""
    parser = argparse.ArgumentParser(
        description="Generate heatmaps from TTM Details CSV reports"
    )
    parser.add_argument(
        "--input",
        "-i",
        nargs="+",
        help="Input CSV file(s). Can be specific files or glob patterns. "
        "If not specified, will process the most recent new_ttm_details_*.csv file in data/reports/",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for heatmaps (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--aggs",
        nargs="+",
        default=DEFAULT_AGGS,
        choices=["median", "mean", "p85"],
        help=f"Aggregation functions to use (default: {' '.join(DEFAULT_AGGS)})",
    )
    parser.add_argument(
        "--threshold-devlt",
        type=float,
        default=DEFAULT_THRESHOLDS["DevLT"],
        help=f"Threshold for DevLT metric (default: {DEFAULT_THRESHOLDS['DevLT']})",
    )
    parser.add_argument(
        "--threshold-tail",
        type=float,
        default=DEFAULT_THRESHOLDS["Tail"],
        help=f"Threshold for Tail metric (default: {DEFAULT_THRESHOLDS['Tail']})",
    )
    parser.add_argument(
        "--threshold-ttm-adj",
        type=float,
        default=DEFAULT_THRESHOLDS["TTM_adj"],
        help=f"Threshold for TTM_adj metric (default: {DEFAULT_THRESHOLDS['TTM_adj']})",
    )

    args = parser.parse_args()

    # Build thresholds dict
    thresholds = {
        "DevLT": args.threshold_devlt,
        "Tail": args.threshold_tail,
        "TTM_adj": args.threshold_ttm_adj,
    }

    # Determine input files
    input_files: List[str] = []
    if args.input:
        for pattern in args.input:
            # Expand glob patterns
            matches = glob.glob(pattern)
            if matches:
                input_files.extend(matches)
            else:
                # If no glob match, treat as literal path
                if os.path.exists(pattern):
                    input_files.append(pattern)
                else:
                    logger.warning(f"Input file not found: {pattern}")
    else:
        # Default: find the most recent new_ttm_details_*.csv in data/reports/
        default_pattern = "data/reports/new_ttm_details_*.csv"
        all_files = glob.glob(default_pattern)
        if not all_files:
            logger.error(
                f"No input files found matching pattern: {default_pattern}. "
                "Please generate a TTM Details report first or specify input files with --input"
            )
            sys.exit(1)
        # Sort by modification time and take the most recent
        most_recent = max(all_files, key=os.path.getmtime)
        input_files = [most_recent]
        log(f"Auto-detected most recent CSV: {most_recent}")

    if not input_files:
        logger.error("No input files specified or found. Use --input or --help")
        sys.exit(1)

    # Create output directory
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    # Process each file
    log(f"Processing {len(input_files)} file(s)...")
    for csv_path in input_files:
        try:
            log(f"Processing: {csv_path}")
            generate_for_file(csv_path, args.output_dir, args.aggs, thresholds)
        except Exception as e:
            logger.error(f"Failed to process {csv_path}: {e}", exc_info=True)

    log("✅ Heatmap generation complete!")
    log(f"Output directory: {args.output_dir}")


if __name__ == "__main__":
    main()
