import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src import dashboard


class DashboardTests(unittest.TestCase):
    def test_saved_comparison_totals(self):
        data = dashboard.load_run("20260914T084039794325Z")
        self.assertEqual(len(data["models"]), 3)
        for model in data["models"]:
            rows, summary = model["items"], model["summary"]
            self.assertEqual(len(rows), int(summary["items"]))
            self.assertEqual(
                sum(row["correct"] == "True" for row in rows), int(summary["correct"])
            )
            self.assertEqual(
                sum(row["status"] == "parse_error" for row in rows),
                int(summary["parse_errors"]),
            )

    def test_unknown_run_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Run not found"):
            dashboard.load_run("../../data")

    def test_snapshot_precedes_current_dataset(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = root / "results" / "example"
            profile = run / "baseline"
            profile.mkdir(parents=True)
            (run / "comparison.csv").write_text("profile,model\nbaseline,test\n")
            (profile / "per_item.csv").write_text("id,expected\n001,Insurance\n")
            (run / "items.jsonl").write_text(
                json.dumps({"id": "001", "clause": "Saved clause"}) + "\n"
            )
            with patch.object(dashboard, "ROOT", root):
                data = dashboard.load_run("example")
            self.assertEqual(data["clause_source"], "snapshot")
            self.assertEqual(data["items"][0]["clause"], "Saved clause")


if __name__ == "__main__":
    unittest.main()
