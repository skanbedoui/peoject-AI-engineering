# Project 0 - Legal Clause Classification

## Task and data

The task is binary legal-clause classification: given a category definition and one contract clause, decide whether the clause contains that category. The supplied `category_descriptions.csv` defines 45 categories but contains no contract clauses or labels. For this local pipeline run, 50 short synthetic clauses were constructed from those definitions, balanced between Yes and No. Labels are clear by construction but are not a substitute for two-person labeling of real contracts.

Example: category `Audit Rights`, clause `Customer may audit Supplier's relevant books and records once each year`, expected answer `Yes`.

## Setup

The evaluated open-weights model was local Ollama `llama3.1:latest`, Llama architecture, 8.0B parameters, Q4_K_M quantization. Every item used the same system prompt, category definition, clause, parser, temperature 0, and one sequential model call. The host CPU was AMD Ryzen 7 7700. API models were not run because API keys are not available yet.

## Results

| Model | Correct | Accuracy | Parse errors | Timeouts | p50 latency (ms) | p95 latency (ms) | Output tok/s | Self-hosted cost / 1k |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| llama3.1:latest | 42/50 | 84% | 0 | 0 | 2088.49 | 2108.35 | 0.69 | $2.50* |

The first three wrong answers were false negatives: Non-Compete item 002, Exclusivity item 004, and No-Solicit of Customers item 006. Five additional false negatives occurred in items 010, 014, 020, 022, and 042. No parse errors or timeouts occurred.

## Choice and cost

There is not yet a three-model choice because the two API models are pending credentials. For the current offline requirement, I would choose `llama3.1:latest`: it is available locally, has no API dependency, and achieved 84% on this controlled set. I would change that choice if a tested API model materially improves accuracy or p95 latency at the target traffic and its cost is acceptable, or if the real-clause evaluation shows unacceptable false negatives.

At 100 times this 50-item run, the current self-hosted assumption estimates $12.50 for 5,000 requests. The $2.50 per 1,000 estimate assumes $0.30/hour and 120 requests/hour; GPU, memory, power, and measured hourly cost still need to be recorded. API break-even volume cannot be calculated until API prices and measured token usage are available.
