# Known issues and validity decisions

## Adaptive prompt-delivery error

The first attempted adaptive Levels 2–6 were routed to the fixed prompt
directory. A later audit inspected the actual input stored in each `.eval`
archive, classified those batches as `FIXED_PROMPT_DELIVERED`, and excluded
them. Levels 2–6 were rerun with delivery verification. Only the selected
verified batches appear in `data/final/final_72_run_dataset.csv`.

## Placement-tool context

Early prompts exposed `place_entity` but did not clearly expose FLE's placement
helpers. Across adaptive Levels 1–6, the placement-grid audit found 1,037
recorded placement failures with coordinates; 635 (61.2%) used incompatible
grid alignment. A separate validation showed that `nearest_buildable` and
`can_place_entity` could guide successful placement when included in context.
The later adaptive prompts incorporated concise helper guidance.

## FLE 0.4.3 compatibility changes

The collection environment used local changes inside the FLE installation:

1. The Python response parser selected the final executable code block instead
   of concatenating every fenced block.
2. Full per-turn program code was retained in trajectory storage so the static
   code scorer received executed programs.
3. The trajectory schema included a `program_codes` list field shared by the
   solver and scorer paths.

These changes corrected observed parser and code-scoring failures. They were
made in the local virtual environment, not in upstream FLE. The original patch
files were not preserved in the final research package, so `scripts/preflight.py`
checks the required behavior instead of silently editing an installed package.
Do not treat a new FLE version as equivalent without revalidating these checks.

## Reporting-code archive gap

The original batch runner calls two project-local reporting programs. Those
reporter source files were not present in the final team archive used to create
this public repository. The derived CSVs, workbooks, readable logs, and raw
archive hash manifest are preserved. The runner therefore supports
`--skip-reporting` for new validation runs. A full reproduction should restore
or independently implement the reporting layer before collecting a new formal
dataset.

## Hardware and environment

The formal runs used one local GPU and were executed sequentially with thermal
checks and cooldown periods. Timing measures may reflect the particular GPU,
Ollama build, WSL2/Docker configuration, and background system load.

