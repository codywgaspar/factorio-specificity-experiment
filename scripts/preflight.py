#!/usr/bin/env python3
"""Read-only checks for the released data and a local FLE installation."""

from __future__ import annotations

import importlib.metadata
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
failures: list[str] = []
warnings: list[str] = []


def check(condition: bool, message: str) -> None:
    print(("PASS" if condition else "FAIL") + ": " + message)
    if not condition:
        failures.append(message)


for arm in ("fixed", "adaptive"):
    prompt_dir = ROOT / "prompts" / arm
    check(
        all((prompt_dir / f"level_{level:02d}.txt").is_file() for level in range(1, 13)),
        f"{arm} prompt set contains Levels 1-12",
    )

dataset_path = ROOT / "data" / "final" / "final_72_run_dataset.csv"
check(dataset_path.is_file(), "final run-level dataset exists")
if dataset_path.is_file():
    dataset = pd.read_csv(dataset_path)
    check(len(dataset) == 72, "final dataset contains 72 runs")
    counts = dataset.groupby(["selected_arm", "selected_level"]).size()
    check(len(counts) == 24 and (counts == 3).all(), "every arm-level cell has three runs")

try:
    fle_version = importlib.metadata.version("factorio-learning-environment")
    print(f"INFO: installed FLE version is {fle_version}")
    if fle_version != "0.4.3":
        warnings.append("The formal experiment used FLE 0.4.3")
except importlib.metadata.PackageNotFoundError:
    fle_version = None
    warnings.append("FLE is not installed; analysis-only use is still available")

if fle_version:
    try:
        from fle.agents.llm.parsing import PythonParser

        fence = "```"
        response = (
            f"{fence}python\nprint('OLD')\n{fence}\n"
            f"{fence}python\nprint('FINAL')\n{fence}"
        )
        result = PythonParser.extract_all_backtick_blocks(response)
        check(result == "print('FINAL')", "FLE parser selects only the final code block")
    except Exception as error:
        failures.append(f"Could not test the FLE parser: {error}")
        print(f"FAIL: Could not test the FLE parser: {error}")

    try:
        import fle.eval.inspect.integration.solver_variants as variants

        fields = variants.TrajectoryData.model_fields
        check("program_codes" in fields, "TrajectoryData contains program_codes")
    except Exception as error:
        failures.append(f"Could not test TrajectoryData: {error}")
        print(f"FAIL: Could not test TrajectoryData: {error}")

for warning in warnings:
    print("WARNING:", warning)

if failures:
    print(f"\nPreflight failed with {len(failures)} issue(s).")
    sys.exit(1)

print("\nPreflight passed.")

