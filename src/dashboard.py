"""Serve the benchmark dashboard using Python's standard library."""

import argparse
import csv
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "frontend"


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def runs():
    return sorted(
        (p.parent.name for p in (ROOT / "results").glob("*/comparison.csv")),
        reverse=True,
    )


def load_run(name):
    if name not in runs():
        raise ValueError("Run not found")
    directory = ROOT / "results" / name
    summaries = read_csv(directory / "comparison.csv")
    models = []
    for summary in summaries:
        profile = summary["profile"]
        path = (directory / profile).resolve()
        if path.parent != directory.resolve():
            raise ValueError("Invalid profile")
        models.append({"summary": summary, "items": read_csv(path / "per_item.csv")})
    snapshot = directory / "items.jsonl"
    with (snapshot if snapshot.exists() else ROOT / "data" / "items.jsonl").open(
        encoding="utf-8-sig"
    ) as handle:
        items = [json.loads(line) for line in handle if line.strip()]
    return {
        "run": name,
        "models": models,
        "items": items,
        "clause_source": "snapshot" if snapshot.exists() else "current_dataset",
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB), **kwargs)

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path.startswith("/api/"):
            try:
                if url.path == "/api/runs":
                    data = runs()
                elif url.path == "/api/run":
                    data = load_run(parse_qs(url.query).get("id", [""])[0])
                else:
                    raise ValueError("Endpoint not found")
                body = json.dumps(data).encode()
                self.send_response(200)
            except (OSError, ValueError, KeyError) as exc:
                body = json.dumps({"error": str(exc)}).encode()
                self.send_response(400)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        else:
            super().do_GET()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Dashboard: http://127.0.0.1:{args.port}", flush=True)
    server.serve_forever()
