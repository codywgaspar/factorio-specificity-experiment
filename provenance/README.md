# Provenance

`batch_snapshots/` contains the manifests and prompt snapshots for the 24
selected formal batches. These records preserve model, seed, turn budget,
prompt hashes, run status, and hardware samples.

`raw_eval_manifest.csv` identifies the 72 original Inspect `.eval` archives by
path, size, and SHA-256 digest. The paths have been redacted to use
`<PROJECT_ROOT>` in this public copy. The archives themselves were omitted due
to size and because the repository already includes complete derived tables and
English-language logs.

