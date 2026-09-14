from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit, urlunsplit

if __package__:
    from .cost import cost_at_traffic, hardware_hourly_cost, self_hosted_cost_per_1000
    from .prompt import SYSTEM_PROMPT, build_prompt, load_categories
    from .score import score
else:
    from cost import cost_at_traffic, hardware_hourly_cost, self_hosted_cost_per_1000
    from prompt import SYSTEM_PROMPT, build_prompt, load_categories
    from score import score

ROOT = Path(__file__).resolve().parents[1]
ITEMS = ROOT / "data" / "items.jsonl"
RESULTS = ROOT / "results"
MODEL = "llama3.1:latest"
MODEL_PROFILES = {
    "baseline": MODEL,
    "top-local": "llama3.2:3b",
    "cheap-local": "llama3.2:1b",
}
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")
MAX_OUTPUT_TOKENS = 24
PER_ITEM_FIELDS = (
    "id",
    "expected",
    "output",
    "parsed",
    "correct",
    "status",
    "error",
    "latency_ms",
    "input_tokens",
    "output_tokens",
    "eval_count",
    "eval_duration",
    "eval_duration_ms",
    "generation_tokens_per_second",
)
SUMMARY_FIELDS = (
    "model",
    "task",
    "run_date_utc",
    "items",
    "categories",
    "correct",
    "accuracy",
    "parse_errors",
    "timeouts",
    "errors",
    "p50_latency_ms",
    "p95_latency_ms",
    "output_tokens_per_second",
    "measured_requests_per_hour",
    "max_output_tokens",
    "self_hosted_cost_per_1000_requests_usd",
    "self_hosted_cost_at_100x_traffic_usd",
)


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def load_items(path: Path = ITEMS) -> list[dict]:
    with path.open(encoding="utf-8-sig") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def validate_items(items: list[dict], categories: dict[str, str]) -> None:
    if len(items) < 50:
        raise ValueError("Benchmark requires at least 50 items")
    ids, clauses, counts = set(), set(), Counter()
    for index, item in enumerate(items, 1):
        if not isinstance(item, dict):
            raise ValueError(f"Item {index} must be an object")
        for field in ("id", "clause", "expected", "source"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ValueError(f"Item {index}: {field} must be a non-empty string")
        identifier = item["id"].strip()
        clause = " ".join(item["clause"].split()).casefold()
        if identifier in ids:
            raise ValueError(f"Duplicate id: {identifier}")
        if clause in clauses:
            raise ValueError(f"Duplicate clause: {identifier}")
        if item["expected"] not in categories:
            raise ValueError(f"Unknown expected category: {item['expected']}")
        ids.add(identifier)
        clauses.add(clause)
        counts[item["expected"]] += 1
    if any(count < 2 for count in counts.values()):
        raise ValueError("Every tested category requires at least 2 examples")


def call_ollama(item: dict, categories: dict[str, str], model: str = MODEL) -> dict:
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(item["clause"], categories)},
        ],
        "options": {"temperature": 0, "num_predict": MAX_OUTPUT_TOKENS},
    }
    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    row = dict.fromkeys(PER_ITEM_FIELDS, "")
    row.update(id=item["id"], expected=item["expected"], correct=False)
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            raw = response.read()
        row["latency_ms"] = (time.perf_counter() - started) * 1000
        body = json.loads(raw.decode("utf-8"))
        if not isinstance(body, dict) or body.get("error"):
            raise ValueError(f"Ollama error response: {body}")
        message = body.get("message")
        if (
            body.get("done") is not True
            or not isinstance(message, dict)
            or not isinstance(message.get("content"), str)
        ):
            raise ValueError("Malformed or incomplete Ollama response")
        row["output"] = message["content"]
        for source, target in (
            ("prompt_eval_count", "input_tokens"),
            ("eval_count", "output_tokens"),
            ("eval_duration", "eval_duration"),
        ):
            value = body.get(source)
            if value is not None:
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise ValueError(f"Invalid Ollama metric: {source}")
                row[target] = value
        row["eval_count"] = row["output_tokens"]
        duration = row["eval_duration"]
        if duration != "":
            row["eval_duration_ms"] = duration / 1e6
        if duration != "" and duration > 0 and row["eval_count"] != "":
            row["generation_tokens_per_second"] = row["eval_count"] / (duration / 1e9)
        row["correct"], parsed = score(row["output"], item["expected"], categories)
        row["parsed"] = parsed or ""
        row["status"] = "ok" if parsed is not None else "parse_error"
        if parsed is None:
            row["error"] = "Output is not an exact allowed category name"
    except (OSError, ValueError, TypeError) as exc:
        if row["latency_ms"] == "":
            row["latency_ms"] = (time.perf_counter() - started) * 1000
        timeout = isinstance(exc, TimeoutError) or (
            isinstance(exc, urllib.error.URLError)
            and isinstance(exc.reason, TimeoutError)
        )
        row.update(
            correct=False,
            parsed="",
            status="timeout" if timeout else "error",
            error=str(exc),
        )
    return row


def summarize(
    rows: list[dict],
    category_count: int,
    elapsed: float,
    hourly_cost: float | None,
    model: str = MODEL,
) -> dict:
    rate = len(rows) * 3600 / elapsed if elapsed > 0 else 0
    cost = self_hosted_cost_per_1000(hourly_cost, rate)
    measured = [r for r in rows if r["generation_tokens_per_second"] != ""]
    duration = sum(r["eval_duration"] for r in measured) / 1e9
    tokens = sum(r["eval_count"] for r in measured)
    correct = sum(r["correct"] for r in rows)
    latencies = [r["latency_ms"] for r in rows]
    return dict(
        zip(
            SUMMARY_FIELDS,
            (
                model,
                "multiclass_legal_clause_classification",
                datetime.now(timezone.utc).isoformat(),
                len(rows),
                category_count,
                correct,
                correct / len(rows),
                sum(r["status"] == "parse_error" for r in rows),
                sum(r["status"] == "timeout" for r in rows),
                sum(r["status"] == "error" for r in rows),
                percentile(latencies, 0.5),
                percentile(latencies, 0.95),
                tokens / duration if duration else None,
                rate,
                MAX_OUTPUT_TOKENS,
                cost,
                cost_at_traffic(len(rows) * 100, cost),
            ),
        )
    )


def command_output(args: list[str]) -> str:
    try:
        return (
            subprocess.check_output(
                args, text=True, timeout=10, stderr=subprocess.DEVNULL
            ).strip()
            or "Unavailable"
        )
    except (OSError, subprocess.SubprocessError):
        return "Unavailable"


def hardware_note(rate: float, hourly_cost: float | None, model: str = MODEL) -> str:
    cpu = platform.processor() or "Unavailable"
    ram = "Unavailable"
    if platform.system() == "Windows":
        detected = command_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Name",
            ]
        )
        if detected != "Unavailable":
            cpu = detected
        total = command_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory",
            ]
        )
        if total.isdigit():
            ram = f"{int(total) / 2**30:.2f} GiB"
    else:
        try:
            ram = f"{os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') / 2**30:.2f} GiB"
        except (AttributeError, OSError, ValueError):
            pass
    gpu = command_output(
        ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"]
    )
    return (
        f"# Hardware note\n\nModel: {model}\n\nOS: {platform.platform()}\n\n"
        f"CPU: {cpu}\n\nLogical CPUs: {os.cpu_count() or 'Unavailable'}\n\n"
        f"Total RAM: {ram}\n\nGPU / VRAM (NVIDIA detection): {gpu}\n\n"
        f"Measured requests/hour: {rate:.2f}\n\n"
        f"Hardware USD/hour: {hourly_cost if hourly_cost is not None else 'Unavailable'}\n\n"
        "Power draw: Unavailable; measure manually.\n\n"
        "Hardware detection describes the runner host; confirm the Ollama server is on this host.\n"
    )


def run_model(
    items: list[dict],
    categories: dict[str, str],
    hourly_cost: float | None,
    model: str,
    destination: Path,
) -> dict:
    destination.mkdir(parents=True, exist_ok=True)
    rows = []
    started = time.perf_counter()
    with (destination / "per_item.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=PER_ITEM_FIELDS)
        writer.writeheader()
        for item in items:
            row = call_ollama(item, categories, model)
            rows.append(row)
            writer.writerow(row)
            handle.flush()
            verdict = "correct" if row["correct"] else "wrong"
            print(
                f"{item['id']} | expected={item['expected']} | predicted={row['parsed'] or row['status']} | {verdict} | {row['latency_ms']:.0f} ms",
                flush=True,
            )
    summary = summarize(
        rows, len(categories), time.perf_counter() - started, hourly_cost, model
    )
    with (destination / "summary.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerow(summary)
    (destination / "hardware.md").write_text(
        hardware_note(summary["measured_requests_per_hour"], hourly_cost, model),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Local multiclass legal clause benchmark"
    )
    parser.add_argument("--validate-only", action="store_true")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--profile", choices=MODEL_PROFILES, default="baseline")
    selection.add_argument(
        "--compare", action="store_true", help="Run all three local models sequentially"
    )
    args = parser.parse_args()
    categories = load_categories(ROOT / "category_descriptions.csv")
    items = load_items()
    validate_items(items, categories)
    hourly_cost = hardware_hourly_cost()
    if args.validate_only:
        print(
            f"Validated {len(items)} items across {len(categories)} allowed categories"
        )
        return
    # Each invocation has its own directory, preserving previous measurements.
    destination = RESULTS / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    profiles = (
        MODEL_PROFILES if args.compare else {args.profile: MODEL_PROFILES[args.profile]}
    )
    endpoint = urlsplit(OLLAMA_URL)
    tags_url = urlunsplit((endpoint.scheme, endpoint.netloc, "/api/tags", "", ""))
    with urllib.request.urlopen(tags_url, timeout=10) as response:
        installed = json.load(response)["models"]
    by_name = {entry["name"]: entry for entry in installed}
    missing = [model for model in profiles.values() if model not in by_name]
    if missing:
        raise ValueError(
            "Models not installed; run: "
            + "; ".join(f"ollama pull {model}" for model in missing)
        )
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "items.jsonl").write_text(
        "\n".join(json.dumps(item) for item in items) + "\n",
        encoding="utf-8",
    )
    (destination / "models.json").write_text(
        json.dumps(
            {role: by_name[model] for role, model in profiles.items()}, indent=2
        ),
        encoding="utf-8",
    )
    (destination / "protocol.json").write_text(
        json.dumps(
            {
                "system_prompt": SYSTEM_PROMPT,
                "categories": categories,
                "temperature": 0,
                "max_output_tokens": MAX_OUTPUT_TOKENS,
                "timeout_seconds": 180,
                "hardware_cost_per_hour_usd": hourly_cost,
                "sequential": True,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    with (destination / "comparison.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=("profile", *SUMMARY_FIELDS))
        writer.writeheader()
        for profile, model in profiles.items():
            print(f"Running {profile}: {model}", flush=True)
            summary = run_model(
                items, categories, hourly_cost, model, destination / profile
            )
            writer.writerow({"profile": profile, **summary})
            handle.flush()
    print(f"Results: {destination}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError) as exc:
        sys.exit(f"Benchmark failed: {exc}")
