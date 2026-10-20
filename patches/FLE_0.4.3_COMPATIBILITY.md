# FLE 0.4.3 compatibility record

The formal environment used `factorio-learning-environment==0.4.3` plus three
local compatibility changes. This file records the required behavior because
the exact modified site-package files were not included in the final archive.

## Required parser behavior

When a model response contains multiple fenced Python blocks, only the final
valid block should be executed. The original local parser concatenated all
blocks, which could execute an abandoned attempt and its correction together.

Expected test:

```python
from fle.agents.llm.parsing import PythonParser

response = """```python
print('OLD')
```
```python
print('FINAL')
```"""

assert PythonParser.extract_all_backtick_blocks(response) == "print('FINAL')"
```

## Required trajectory behavior

`TrajectoryData.model_fields` must include `program_codes`, with a default
empty list. The solver must append each executed program and store the list in
the trajectory record before scoring. This is required for a meaningful static
code score.

## Why this is not an automatic patch

These files are internal FLE implementation details. Line-level patches are
version-sensitive and can silently corrupt a newer release. Run
`scripts/preflight.py`, inspect failures, and either use a dependency revision
that already provides the behavior or port the changes with tests.

