# Factorio Specificity Experiment

Reproducibility materials for a 72-run experiment testing how fixed cumulative
instructions and human-adaptive prompt interventions affect an LLM agent in
the [Factorio Learning Environment](https://github.com/JackHopkins/factorio-learning-environment).

## Experiment at a glance

| Item | Value |
|---|---:|
| Experimental arms | Fixed and adaptive |
| Cumulative levels per arm | 12 |
| Independent runs per level | 3 |
| Turns per run | 150 |
| Formal runs | 72 |
| Model | Gemma 4 26B through Ollama |
| Reasoning mode | Disabled |
| Map seed | 44340 |
| FLE version | 0.4.3 |
| Python version | 3.12.14 |

Across all 36 runs in each arm, the adaptive arm had 32.9% higher mean raw
production, 42.3% higher mean automated production, and 42.6% fewer errors.
Production per 1,000 ticks was nearly unchanged (-0.6%), so the raw-score gains
should be interpreted alongside run duration and activity. These are
descriptive comparisons, not causal estimates from a large-sample study.

## Start here

- [`docs/FILE_GUIDE.md`](docs/FILE_GUIDE.md) explains every directory.
- [`docs/METHODS.md`](docs/METHODS.md) describes the experimental design.
- [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md) gives setup and rerun steps.
- [`docs/KNOWN_ISSUES.md`](docs/KNOWN_ISSUES.md) documents validity issues and
  the local FLE compatibility changes used during collection.
- [`data/final/FLE_final_results.xlsx`](data/final/FLE_final_results.xlsx) is the
  main results workbook.
- [`data/final/final_72_run_dataset.csv`](data/final/final_72_run_dataset.csv)
  is the analysis-ready run-level dataset.
- [`data/final/FLE_FDI_sensitivity_analysis.xlsx`](data/final/FLE_FDI_sensitivity_analysis.xlsx)
  contains the Factor Development Index and weight sensitivity analysis.

## Reproduce the published analysis

```bash
python -m venv .venv
source .venv/bin/activate
pip install pandas openpyxl numpy
python scripts/rebuild_summary.py
```

This recreates the arm-level and level-by-arm CSV summaries from the released
72-run dataset without requiring Factorio, Docker, FLE, or a local model.

## Run new Factorio batches

The original environment used Windows 11, WSL2 Ubuntu, Docker Desktop with WSL
integration, an NVIDIA GPU, and Ollama running on Windows.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
fle cluster start
python scripts/preflight.py
```

Then run a validation before any formal batch:

```bash
python scripts/run_factorio_batch.py \
  --arm fixed \
  --level 1 \
  --repeats 1 \
  --turns 3 \
  --validation \
  --prompt-dir prompts/fixed \
  --skip-reporting
```

The formal design uses exactly three 150-turn runs per condition. See the
reproducibility guide before starting because map-reset verification, model
configuration, prompt provenance, and FLE compatibility all affect validity.

## Repository contents

```text
data/          Final datasets, workbooks, and per-level report tables
prompts/       Fixed and adaptive cumulative instruction increments
reviews/       Human review records used to choose adaptive interventions
logs/          English-language logs for all 72 formal runs
experiments/   Inspect/FLE task adapters
scripts/       Batch runner, preflight, and analysis utilities
audits/        Prompt-delivery, placement, and batch-selection audits
provenance/    Selected manifests, prompt snapshots, and raw-log hashes
patches/       Compatibility notes for the FLE 0.4.3 environment
docs/          Methods, file guide, data dictionary, and limitations
```

## Validity note

The first attempted adaptive Levels 2–6 accidentally received the fixed-arm
prompt directory. The prompt-delivery audit detected the error; those runs were
excluded and replaced with verified reruns. The final 72-run dataset contains
only the selected formal batches. See `audits/adaptive_prompt_delivery_audit.*`
and `reviews/excluded_adaptive_batches.csv`.

## Licenses

- Code: [MIT](LICENSE-CODE)
- Documentation, prompts, and released data: [CC BY 4.0](LICENSE-DATA)

Factorio, FLE, Gemma, Ollama, Inspect, and other dependencies retain their own
licenses and trademarks.

