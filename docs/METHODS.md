# Methods

## Research question

The experiment examined how increasing prompt specificity affects an LLM
agent's ability to make productive, automated progress in Factorio, and whether
human review between levels can improve later instructions.

## Design

The study used two arms:

1. **Fixed arm:** twelve instruction increments were defined before collection.
2. **Adaptive arm:** the Level 1 condition was shared with the fixed baseline;
   each later increment was selected after reviewing the previous level's three
   runs and documenting observed strengths, failures, and alternatives.

Instructions were cumulative within each arm. At Level 6, for example, the
model received increments 1 through 6 for that arm.

Each arm contained 12 levels, with three independent 150-turn runs per level,
for 72 formal runs. All formal runs used map seed 44340, Gemma 4 26B through
Ollama, a 16,384-token context, and disabled model reasoning output.

## Run independence

Before every run, the Factorio container was restarted and the scenario reset.
The batch runner checked the fixed map seed, resource regeneration, entity
clearing, production-stat reset, research reset, and environment reset hook.
Every run wrote its own manifest, prompt snapshot, console log, Inspect archive,
and derived reports.

## Measures

Primary behavioral outputs included:

- production score;
- automated production score;
- automation ratio;
- errors and error rate;
- productive turns and productive-turn rate;
- longest error and repeated-action streaks;
- production and automated production per 1,000 ticks;
- technologies, achievements, and produced item types.

The Factor Development Index (FDI) was explored after data collection as a
normalized composite measure. Because index conclusions depend on weights and
normalization choices, the released sensitivity workbook presents alternatives
rather than treating one weighting scheme as uniquely correct.

## Adaptive review process

After each adaptive level, the team reviewed all three readable logs and the
batch-level behavior/error tables. The next intervention targeted repeated
patterns supported by multiple runs. Completed review records and the actual
prompt increments are preserved in `reviews/` and `prompts/adaptive/`.

## Analysis scope

With only three runs per arm-level cell, cell means and standard deviations are
descriptive and uncertain. The dataset supports exploratory modeling and
sensitivity analysis, but strong causal or population-level claims should not
be based on a single level's three observations.

