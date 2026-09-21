# Legal Clause Classification

## Project 0 - Postmortem

**Updated:** September 14, 2026  
**Scope:** Binary-to-multiclass refactor, three-model local comparison, and results dashboard.

## 1. What Changed

The first version asked whether a clause matched a supplied category and returned Yes or No. Supplying the candidate label made that task weaker as a genuine classification benchmark. The refactor asks the model to choose one label from the full catalogue.

The project now validates 50 synthetic items across 25 categories, sends one sequential request per item, parses exact category names, and records per-item predictions plus aggregate measurements. The system prompt incorporates 1-shot output format guidance, contrastive boundary rules, hard-pair few-shot guidance, and a mode-collapse default guard. Three local Llama models temporarily occupy the baseline, top-local, and cheap-local experiment roles.

A read-only dashboard makes the saved results inspectable through charts, category comparisons, filters, raw-output details, and CSV export. Separate run directories preserve evidence instead of overwriting the previous experiment.

## 2. What Worked

**The pipeline exposed meaningful differences.** The 8B baseline scored 50/50, the 3B replacement 39/50, and the 1B replacement 5/50. All 150 calls completed without timeouts or server errors.

**Prompt engineering targeted specific failure modes.** Incorporating 1-shot output formatting, contrastive boundary rules, hard-pair few-shot guidance, and a default guard directly addressed the output hallucinations and category confusion observed in smaller models.

**Strict parsing made output failures visible.** The 3B model returned two labels outside the catalogue. They were recorded as parse errors and counted as wrong rather than accepted through a permissive substring match.

**Per-item evidence supported diagnosis.** The dashboard reveals that the 1B model often selected Non-Compete for unrelated clauses. A valid output format alone was clearly insufficient.

**Measurement improved.** Generation speed uses Ollama generation duration rather than total request latency. Self-hosted cost uses measured request throughput and an optional explicit hourly assumption.

## 3. Problems and Lessons

### Task framing

Binary recognition and multiclass classification answer different questions. The old result could not be reused after changing the task. Reports and exports must be updated together when the benchmark contract changes.

### Data quality

The supplied category CSV contains definitions, not labeled contract excerpts. Synthetic clauses made the pipeline testable, but 50 examples and two items per category are too small and too controlled to support real-world claims. The 8B model's perfect score should motivate a stronger evaluation set, not a general legal-accuracy claim.

### Small-model behavior

The 3B model confused general license grants with specialized restrictions and sometimes invented labels. The 1B model mostly produced well-formed but incorrect answers. These results apply to the unchanged prompt and catalogue; identifying the cause would require a separate controlled experiment.

### Timing and economics

The first request for each model included a different startup cost. Cached prompts and model residency can also affect timing. Generation speed and whole-request latency must be reported separately. The model variants use different quantization levels, so this is not a controlled parameter-count-only study.

A fixed requests/hour assumption would have hidden these differences. Cost remains blank until an hourly assumption is documented; hardware cost and power measurements still require manual work.

### Repository and report drift

An obsolete PDF script hardcoded the old binary result even after the Markdown report changed. It was replaced with a Markdown-driven exporter. Source formatting, result provenance notes, and dashboard data tests now make the project easier to maintain. Recorded CSVs remain unchanged.

## 4. Current State

| Area                                         | Status                             |
| -------------------------------------------- | ---------------------------------- |
| Multiclass validation and strict scoring     | Implemented and tested             |
| Three local Llama profiles                   | Installed and evaluated            |
| Saved predictions, summaries, hardware notes | Available                          |
| Performance dashboard                        | Implemented; reads saved results   |
| Markdown and PDF reports                     | Updated from the same source       |
| Independent real-clause dataset              | Pending                            |
| Two-person label verification                | Pending                            |
| Actual API comparison                        | Pending; no API code or keys added |
| Hardware cost and power measurement          | Pending                            |

The local top/cheap names are temporary roles. The 3B replacement is not larger than the 8B baseline and is not equivalent to a top API model.

## 5. Actions Before Final Submission

1. Source real clauses independently, record provenance, and retain one intended label per final item.
2. Have two reviewers independently label each item and document how disagreements are resolved.
3. Freeze the dataset, definitions, prompt, model versions, and measurement settings before evaluation.
4. Run the same frozen test on the actual API models once that work is authorized.
5. Document hardware, power, cost assumptions, and the startup/cache protocol.
6. Rebuild the PDFs from the final Markdown and verify their results against the saved CSVs.

## 6. Evidence

The current comparison is [run 20260914T084039794325Z](results/20260914T084039794325Z/comparison.csv). See [the experiment report](report.md) for measurements, example mistakes, cost formulas, and limitations, and [the README](README.md) for setup and repository structure.
