#!/usr/bin/env python3
"""Rebuild descriptive arm and level summaries from the released dataset."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "final" / "final_72_run_dataset.csv"
OUTPUT = ROOT / "reproduced_results"

METRICS = [
    "production",
    "automated",
    "automation_ratio",
    "errors",
    "error_rate",
    "productive_turns",
    "productive_rate",
    "production_per_1000_ticks",
    "automated_per_1000_ticks",
    "longest_error_streak",
    "longest_repeat_streak",
]


def arm_summary(data: pd.DataFrame) -> pd.DataFrame:
    rows = []
    fixed = data[data["selected_arm"] == "fixed"]
    adaptive = data[data["selected_arm"] == "adaptive"]
    for metric in METRICS:
        fixed_mean = fixed[metric].mean()
        adaptive_mean = adaptive[metric].mean()
        difference = adaptive_mean - fixed_mean
        rows.append(
            {
                "metric": metric,
                "fixed_mean": fixed_mean,
                "fixed_sd": fixed[metric].std(ddof=1),
                "adaptive_mean": adaptive_mean,
                "adaptive_sd": adaptive[metric].std(ddof=1),
                "absolute_change": difference,
                "percent_change": 100 * difference / fixed_mean
                if fixed_mean != 0
                else float("nan"),
            }
        )
    return pd.DataFrame(rows)


def level_summary(data: pd.DataFrame) -> pd.DataFrame:
    aggregates = (
        data.groupby(["selected_level", "selected_arm"], as_index=False)[METRICS]
        .mean()
    )
    rows = []
    for level in sorted(data["selected_level"].unique()):
        fixed = aggregates[
            (aggregates["selected_level"] == level)
            & (aggregates["selected_arm"] == "fixed")
        ].iloc[0]
        adaptive = aggregates[
            (aggregates["selected_level"] == level)
            & (aggregates["selected_arm"] == "adaptive")
        ].iloc[0]
        row = {"level": int(level), "fixed_runs": 3, "adaptive_runs": 3}
        for metric in METRICS:
            fixed_value = fixed[metric]
            adaptive_value = adaptive[metric]
            difference = adaptive_value - fixed_value
            row[f"fixed_{metric}"] = fixed_value
            row[f"adaptive_{metric}"] = adaptive_value
            row[f"{metric}_difference"] = difference
            row[f"{metric}_percent_change"] = (
                100 * difference / fixed_value if fixed_value != 0 else float("nan")
            )
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    data = pd.read_csv(INPUT)
    if len(data) != 72:
        raise SystemExit(f"Expected 72 formal runs, found {len(data)}")
    cell_counts = data.groupby(["selected_arm", "selected_level"]).size()
    if len(cell_counts) != 24 or not (cell_counts == 3).all():
        raise SystemExit("Expected 24 arm-level cells with three runs each")
    OUTPUT.mkdir(exist_ok=True)
    arm = arm_summary(data)
    level = level_summary(data)
    arm.to_csv(OUTPUT / "final_arm_comparison.csv", index=False)
    level.to_csv(OUTPUT / "final_level_comparison.csv", index=False)
    print(f"Validated {len(data)} runs across {len(cell_counts)} cells.")
    print(f"Wrote {OUTPUT / 'final_arm_comparison.csv'}")
    print(f"Wrote {OUTPUT / 'final_level_comparison.csv'}")


if __name__ == "__main__":
    main()

