# File guide

## Results to open first

| File | Purpose |
|---|---|
| `data/final/FLE_final_results.xlsx` | Main workbook with final fixed/adaptive results |
| `data/final/final_72_run_dataset.csv` | One row per formal run; primary analysis table |
| `data/final/final_arm_comparison.csv` | Descriptive comparison of the two arms |
| `data/final/final_level_comparison.csv` | Side-by-side results at each instruction level |
| `data/final/FLE_FDI_sensitivity_analysis.xlsx` | Factor Development Index calculations and alternative weights |
| `data/final/final_selected_batches.csv` | Formal batch-selection record |

## Evidence and provenance

| Directory | Purpose |
|---|---|
| `logs/` | One readable turn-by-turn text log for each formal run plus a register |
| `data/batch_reports/` | Run, behavior, error, phase, and turn tables for each selected batch |
| `prompts/fixed/` | Twelve fixed-arm instruction increments |
| `prompts/adaptive/` | Twelve adaptive-arm instruction increments |
| `reviews/` | Evidence packets and completed human review records |
| `audits/` | Prompt-delivery, placement-grid, and selected-batch checks |
| `provenance/batch_snapshots/` | Prompt snapshots and manifests for the selected batches |
| `provenance/raw_eval_manifest.csv` | Original `.eval` locations, byte sizes, and SHA-256 hashes |

The raw Inspect `.eval` archives are not in this repository. They remain in the
original experiment archive and are identified by the hash manifest.

## Code

| File | Purpose |
|---|---|
| `experiments/specificity_eval.py` | Formal Inspect task and compact Factorio execution contract |
| `scripts/run_factorio_batch.py` | Three-repeat batch orchestration, resets, hardware monitoring, and manifests |
| `scripts/preflight.py` | Checks prompt sets, dependencies, data integrity, and FLE compatibility |
| `scripts/rebuild_summary.py` | Recreates summary CSVs from the released run-level dataset |
| `scripts/compile_fixed_arm.py` | Historical fixed-arm compiler retained for provenance |
| `experiments/placement_helper_validation*.py` | Diagnostic tasks used to isolate placement-tool problems |

