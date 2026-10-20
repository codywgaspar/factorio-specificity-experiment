# Reproducibility guide

## Two reproducibility targets

### Rebuild the released comparisons

This path uses the published run-level CSV and does not need Factorio:

```bash
python -m venv .venv
source .venv/bin/activate
pip install pandas numpy openpyxl
python scripts/rebuild_summary.py
```

Outputs are written to `reproduced_results/`.

### Run new game trajectories

This path requires substantially more infrastructure:

- Python 3.12 (the formal environment used 3.12.14);
- Docker and a running Factorio container through FLE;
- FLE 0.4.3 with Inspect support;
- Ollama reachable through its OpenAI-compatible API;
- `gemma4-fle:26b`, configured for a 16,384-token context;
- enough disk space for Inspect archives and enough cooling for sustained GPU
  load.

FLE currently documents `pip install factorio-learning-environment[eval]`,
`fle cluster start`, and `fle eval`. This repository pins 0.4.3 because that is
the version used during collection.

## Environment setup used by the study

The study ran Ollama on Windows and the experiment in WSL2. In WSL:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

WINDOWS_HOST="$(ip route show | awk '/default/ {print $3; exit}')"
export OPENAI_BASE_URL="http://${WINDOWS_HOST}:11434/v1"
export OPENAI_API_KEY="ollama"
export OLLAMA_BASE_URL="$OPENAI_BASE_URL"
export OLLAMA_API_KEY="ollama"
```

Docker Desktop must expose Docker to the chosen WSL distribution. Confirm with
`docker ps` before starting.

## Prompt selection

Use `prompts/fixed` for the fixed arm and `prompts/adaptive` for the adaptive
arm. The runner concatenates every increment from Level 1 through the requested
level. Adaptive batches require the completed review record that justified the
next increment.

## Preflight

```bash
python scripts/preflight.py
```

Resolve every failed check before formal collection. In particular, verify the
parser's final-block behavior and the trajectory schema's `program_codes`
field. See `patches/FLE_0.4.3_COMPATIBILITY.md`.

## Validation run

```bash
python scripts/run_factorio_batch.py \
  --arm fixed --level 1 --repeats 1 --turns 3 --validation \
  --prompt-dir prompts/fixed --skip-reporting
```

Inspect the resulting manifest, console log, prompt snapshot, and `.eval`
archive. Confirm that the container reset, model endpoint, seed, and prompt hash
are correct.

## Formal fixed-arm run

```bash
python scripts/run_factorio_batch.py \
  --arm fixed --level 1 --repeats 3 --turns 150 \
  --prompt-dir prompts/fixed --skip-reporting
```

## Formal adaptive-arm run

```bash
python scripts/run_factorio_batch.py \
  --arm adaptive --level 2 --repeats 3 --turns 150 \
  --prompt-dir prompts/adaptive \
  --adaptive-review reviews/level_01_completed_review.md \
  --skip-reporting
```

Do not create the next adaptive prompt until all three runs from the current
level have been reviewed and the decision record has been saved.

## Raw archive verification

The public repository provides the raw archive manifest rather than the large
`.eval` files. If the separate raw archive is available, compare each file's
SHA-256 digest to `provenance/raw_eval_manifest.csv` before analysis.

