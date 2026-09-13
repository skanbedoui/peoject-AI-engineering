from __future__ import annotations

import csv
import json
import os
import statistics
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from cost import cost_at_traffic, self_hosted_cost_per_1000
from prompt import SYSTEM_PROMPT, build_prompt
from score import score

ROOT = Path(__file__).resolve().parents[1]
ITEMS = ROOT / "data" / "items.jsonl"
RESULTS = ROOT / "results"
MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:latest")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


def call_ollama(item: dict) -> tuple[str, int, int, float]:
    payload = {
        "model": MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(item["category"], item["description"], item["clause"])},
        ],
        "options": {"temperature": 0},
    }
    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=180) as response:
        body = json.loads(response.read().decode("utf-8"))
    elapsed_ms = (time.perf_counter() - started) * 1000
    content = body.get("message", {}).get("content", "")
    return content, int(body.get("prompt_eval_count", 0)), int(body.get("eval_count", 0)), elapsed_ms


def load_items() -> list[dict]:
    with ITEMS.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    rows: list[dict] = []
    for item in load_items():
        try:
            output, input_tokens, output_tokens, latency_ms = call_ollama(item)
            correct, parsed = score(output, item["expected"])
            status = "ok"
            error = ""
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            output = ""
            parsed = None
            input_tokens = output_tokens = 0
            latency_ms = 0.0
            correct = False
            status = "timeout" if isinstance(exc, TimeoutError) else "error"
            error = str(exc)
        rows.append({
            "id": item["id"],
            "category": item["category"],
            "expected": item["expected"],
            "output": output.replace("\n", " "),
            "parsed": parsed or "",
            "correct": str(correct),
            "status": status,
            "error": error,
            "latency_ms": f"{latency_ms:.2f}",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        })
        print(f"{item['id']} {status} {latency_ms:.0f} ms")

    fields = list(rows[0]) if rows else []
    with (RESULTS / "per_item.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    latencies = [float(row["latency_ms"]) for row in rows if row["status"] == "ok"]
    correct_count = sum(row["correct"] == "True" for row in rows)
    parse_errors = sum(row["status"] == "ok" and not row["parsed"] for row in rows)
    timeouts = sum(row["status"] == "timeout" for row in rows)
    total_output_tokens = sum(int(row["output_tokens"]) for row in rows)
    total_latency_seconds = sum(latencies) / 1000
    tokens_per_second = total_output_tokens / total_latency_seconds if total_latency_seconds else 0
    cost_1k = self_hosted_cost_per_1000()
    summary = {
        "model": MODEL,
        "run_date_utc": datetime.now(timezone.utc).isoformat(),
        "items": len(rows),
        "correct": correct_count,
        "accuracy": correct_count / len(rows) if rows else 0,
        "parse_errors": parse_errors,
        "timeouts": timeouts,
        "p50_latency_ms": round(percentile(latencies, 0.50), 2),
        "p95_latency_ms": round(percentile(latencies, 0.95), 2),
        "output_tokens_per_second": round(tokens_per_second, 2),
        "self_hosted_cost_per_1000_requests_assumption_usd": round(cost_1k, 4),
        "self_hosted_cost_at_100x_traffic_usd": round(cost_at_traffic(len(rows) * 100, cost_1k), 4),
    }
    with (RESULTS / "summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=summary)
        writer.writeheader()
        writer.writerow(summary)
    (RESULTS / "hardware.md").write_text(
        "# Hardware note\n\n"
        f"Model: `{MODEL}`\n\n"
        "Ollama ran locally. Record the machine CPU/GPU, RAM/VRAM, and measured power or hourly cost here before submission. "
        "The current cost estimate uses the assumptions in `src/cost.py`.\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
