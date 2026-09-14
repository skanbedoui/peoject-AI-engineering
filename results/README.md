# Result Provenance

## Current Comparison

`20260914T084039794325Z/` contains the September 14, 2026 three-model comparison: 50 clauses per model, with 50, 39, and 5 correct predictions. This is the run used by the report and dashboard.

`comparison.csv` aggregates completed model summaries. Each profile directory contains its unmodified per-item CSV, summary CSV, and hardware note. `models.json` records installed model digests and metadata.

## Earlier Baseline

The root-level `per_item.csv`, `summary.csv`, and `hardware.md` are the earlier standalone multiclass baseline run, completed at 08:27 UTC on September 14. It scored 50/50. Its cold-start timing differs from the later comparison; do not combine their latency or throughput figures.

These files are historical measurements, not redundant generated clutter. They are retained for provenance.

## New Runs

Each invocation creates a new UTC-stamped directory. New runs retain `items.jsonl`, `protocol.json`, and `models.json` alongside the comparison and per-model outputs. Existing runs were created before dataset/protocol snapshots were added; no snapshot is retroactively claimed for them. The dashboard falls back to current dataset text for those older runs.

An interrupted run may contain partial per-item output. Only completed models receive a row in `comparison.csv`. Final CSVs are intentionally tracked; temporary files are ignored.
