# Contributing

Contributions that improve reproducibility, documentation, portability, or
analysis are welcome.

Before submitting a change:

1. Do not modify the released observations in
   `data/final/final_72_run_dataset.csv`.
2. Keep corrections to raw or derived data explicit and document their source.
3. Run `python -m py_compile experiments/*.py scripts/*.py`.
4. Run `python scripts/rebuild_summary.py` and confirm that the recreated
   summaries match the released CSVs within floating-point tolerance.
5. Never commit API keys, local `.env` files, virtual environments, raw model
   weights, or unredacted machine-specific paths.

For a new experimental dataset, use a new directory or release rather than
overwriting the original 72-run evidence package.

