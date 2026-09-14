# Project 0 - Multiclass Legal Clause Benchmark

The task is legal clause -> one category. Three local Ollama models select exactly one of 25 categories, with definitions loaded from `category_descriptions.csv`. The project includes a reproducible benchmark, strict scoring, a read-only dashboard, and Markdown/PDF reports.

The completed September 14 comparison scored **100% (8B), 78% (3B), and 10% (1B)** on 50 synthetic clauses. See [the report](report.md) for evidence and limitations. Actual API comparisons remain pending.

Example input: "Either party may terminate this Agreement without cause upon thirty days' written notice."
Expected output: `Termination for Convenience`.

## Setup

Requires Python 3.10+ and Ollama running locally. No Python packages or API keys are needed.

```powershell
ollama pull llama3.1:latest
python src/run.py --validate-only
python src/run.py
```

## Local comparison

Three local profiles temporarily fill the experiment slots:

| Profile     | Ollama model    | Role                                 |
| ----------- | --------------- | ------------------------------------ |
| baseline    | llama3.1:latest | Existing 8B baseline                 |
| top-local   | llama3.2:3b     | Larger of the two replacement models |
| cheap-local | llama3.2:1b     | Small-model replacement              |

The role names do not imply API-equivalent quality or cost, or that the 3B model is stronger than the 8B baseline. The two additions are practical candidates for the detected 8 GB GPU. Ollama lists downloads of approximately [2.0 GB for 3B](https://ollama.com/library/llama3.2:3b) and [1.3 GB for 1B](https://ollama.com/library/llama3.2:1b); runtime memory is larger. API integrations remain pending.

```powershell
ollama pull llama3.2:3b
ollama pull llama3.2:1b
python src/run.py --compare
```

Run a single replacement with `python src/run.py --profile top-local` or `python src/run.py --profile cheap-local`. With no flags the runner still uses the baseline. The runner checks that selected models are installed before starting. Models and items run sequentially with identical data, prompts, parser, temperature and output limit.

If the Ollama service is stopped, start it with `ollama serve` in another terminal.
Optional `OLLAMA_URL` overrides the default `http://localhost:11434/api/chat`.

## Dashboard

Start the local performance dashboard (no extra packages):

```powershell
python src/dashboard.py --port 8080
```

Open http://127.0.0.1:8080. Use another port if 8080 is occupied. The dashboard reads saved comparison runs and shows model accuracy, latency, generation speed, per-category performance, searchable predictions, raw outputs, and CSV export. It is read-only and does not make model calls. Reload after a new benchmark to see it in the run selector.

New benchmark runs save a dataset snapshot and the prompt/category protocol beside their results. Older runs without a snapshot use clause text from the current dataset; predictions and scores always come from the saved CSVs.

## Dataset

`data/items.jsonl` contains 50 synthetic development items, two per category:

```json
{
  "id": "001",
  "clause": "During the term, Consultant shall not operate a business competing with Client's payroll services.",
  "expected": "Non-Compete",
  "source": "synthetic"
}
```

See `data/LABELING.md` for label policy and required independent final-data review.
Validation checks minimum size, unique IDs and normalized clauses, nonempty text, allowed labels, and at least two items per tested category before any calls.

Every item receives the same full catalogue and one sequential request, temperature 0, a 24-token output limit, and a 180-second request timeout. There are no retries or judge models. The parser strips surrounding whitespace and accepts only an exact, case-sensitive category name. Prefixes, quotes, extra punctuation, and multiple categories are wrong.

## Outputs and measurement

- `results/<UTC-run>/<profile>/per_item.csv`: raw output, prediction, correctness, status/error, full-response latency, input/output counts, raw eval timing and generation tokens/sec.
- `results/<UTC-run>/<profile>/summary.csv`: accuracy, parse errors, timeouts, other errors, p50/p95 latency, generation throughput, measured request rate, and optional costs.
- `results/<UTC-run>/<profile>/hardware.md`: detected host hardware and missing measurements.
- `results/<UTC-run>/comparison.csv`: one summary row per completed model.
- `results/<UTC-run>/models.json`: installed model tags, digests, and metadata.
- `results/<UTC-run>/items.jsonl`: the dataset used for that run.
- `results/<UTC-run>/protocol.json`: system prompt, category definitions, request settings, and hourly-cost assumption.

Previous baseline results in the root of `results/` are preserved; [result provenance](results/README.md) distinguishes them from the current comparison. Every new invocation writes a separate timestamped directory. Comparison rows are saved after each model completes.

No warm-up calls are added. First-request latency can include model loading, and Ollama may reuse cached models or prompts. Compare latency with this startup/cache caveat; the measured request rate is not a pure steady-state capacity estimate.

Latency percentiles include failed requests. Generation throughput is total eval_count divided by total eval_duration (nanoseconds converted to seconds), using only matched available measurements. Missing token/timing values remain blank. Requests/hour uses the full sequential loop duration, including errors and result-writing overhead.

Optional hardware cost assumption:

```powershell
$env:LOCAL_HARDWARE_COST_PER_HOUR_USD = "0.30"
python src/run.py
```

This is a user-supplied example, not a measured cost. Without the variable, cost fields remain blank. Cost/1,000 = hourly cost / measured requests per hour \* 1,000. Cost at 100x traffic means processing 100 times the benchmark item count at the measured rate; it does not model concurrent capacity or API break-even.

## Limitations

Synthetic smoke tests do not establish real-world legal performance. Categories can overlap; the most specific expressed category takes precedence over a generic grant. There is no Other or multilabel output, so out-of-catalogue clauses are unsuitable. Independent real clauses and two-person label verification remain required. Hardware detection describes the runner, which must be checked if Ollama is remote. GPU detection uses nvidia-smi; other GPUs and power consumption may need manual documentation. API models and comparison are intentionally not implemented yet.

## Repository Map

| Path                                           | Purpose                                                           |
| ---------------------------------------------- | ----------------------------------------------------------------- |
| `src/run.py`                                   | Validation, model requests, scoring orchestration, result writing |
| `src/prompt.py`, `src/score.py`, `src/cost.py` | Category catalogue, strict parsing, cost formulas                 |
| `src/dashboard.py`                             | Local HTTP server and saved-result API                            |
| `frontend/`                                    | Browser markup, styling, and dashboard interactions               |
| `data/`                                        | Synthetic development items and labeling policy                   |
| `category_descriptions.csv`                    | Original category definitions                                     |
| `results/`                                     | Preserved experiment evidence and provenance notes                |
| `tests/`                                       | Benchmark, dashboard data, and saved-result checks                |
| `scripts/export_reports.py`                    | Markdown-to-PDF exporter                                          |
| `report.md`, `postmortem.md`                   | Editable experiment documents                                     |
| `report.pdf`, `postmortem.pdf`                 | Formatted exports of those documents                              |
| `project0-bakeoff.pdf`                         | Original assignment brief; retained unchanged                     |

## Checks and Document Export

The benchmark and dashboard need no third-party packages. Run their checks with:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q src scripts tests
python src/run.py --validate-only
node --check frontend/app.js
```

Optional development dependencies provide Python formatting and PDF export:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m black src scripts tests
npx --yes prettier@3.6.2 --write frontend README.md report.md postmortem.md data/LABELING.md results/README.md
.venv\Scripts\python scripts/export_reports.py
```

Edit the Markdown documents first, then regenerate both PDFs. The exporter does not hardcode experiment results. See [the postmortem](postmortem.md) for lessons and final-submission actions. Generated caches, local tooling, and temporary renders are ignored; source, final PDFs, and measured CSVs are retained.
