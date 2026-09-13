# Project 0 - Legal Clause Bake-Off

This repository evaluates a local Ollama model on a small legal-clause classification task. The supplied `category_descriptions.csv` contains category definitions, not labeled contract clauses, so `data/items.jsonl` is a synthetic, controlled benchmark derived from those definitions. It is suitable for testing the pipeline, not for claiming performance on real contracts.

## Setup and run

Prerequisites: Python 3.10+ and Ollama with `llama3.1:latest` pulled.

```powershell
ollama pull llama3.1:latest
python src/run.py
```

## Dashboard

Install the interface dependencies and launch the local results dashboard:

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

The dashboard reads the committed CSV and JSONL files; it does not call a model. It includes the overview metrics, category breakdown, item explorer, error analysis, protocol, and known limitations. The current repository contains only the local Ollama baseline, so the two API model slots remain explicitly marked as pending.

The runner makes one sequential local call per item and writes `results/per_item.csv`, `results/summary.csv`, and `results/hardware.md`. It uses temperature 0 and a fixed JSON output format. Set `OLLAMA_MODEL` to use another locally installed model.

## Task and data

For each short contract clause, the model answers whether the clause contains the named legal category. The only accepted answers are `Yes` or `No`. The 50 items are balanced across positive and negative examples, and each expected label was written from the clause text by construction. For a graded submission, replace or augment the synthetic items with 50+ independently labeled real clauses, document their source, and have two people check every label.

## Scoring and cost

`src/score.py` parses only the first valid `Yes` or `No`; refusals, malformed output, and timeouts are wrong. Accuracy is reported as `n / total`, plus parse errors and timeouts. Latency is measured from request send until the full response is received, and p50/p95 are reported. `src/cost.py` estimates self-hosted cost from hardware cost per hour and requests per hour; edit the constants for the actual machine and electricity assumption.

## Contributions

- Team member: benchmark pipeline, synthetic data, and local Ollama run.

## Limitations / postmortem

See `postmortem.md`. API comparisons are intentionally pending until API keys are available; this run is the open-weights baseline required by the brief.
