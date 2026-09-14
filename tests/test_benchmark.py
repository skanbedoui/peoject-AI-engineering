import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
import urllib.error
from unittest.mock import patch

from src import run
from src.cost import cost_at_traffic, self_hosted_cost_per_1000
from src.prompt import load_categories
from src.score import parse_answer


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.categories = load_categories(run.ROOT / "category_descriptions.csv")
        self.items = run.load_items()

    def test_data_and_parser(self):
        run.validate_items(self.items, self.categories)
        self.assertEqual(len(self.categories), 25)
        self.assertEqual(
            parse_answer(" \nNon-Compete\t", self.categories), "Non-Compete"
        )
        for text in (
            "Category: Non-Compete",
            "Non-Compete.",
            "I think this is Non-Compete",
            '"Non-Compete"',
            "non-compete",
            "Non-Compete\nInsurance",
            "",
        ):
            self.assertIsNone(parse_answer(text, self.categories))

    def test_invalid_datasets(self):
        mutations = [
            lambda x: x.pop(),
            lambda x: x[1].update(id=x[0]["id"]),
            lambda x: x[1].update(clause="  "),
            lambda x: x[1].update(clause=x[0]["clause"].upper()),
            lambda x: x[1].update(expected="Unknown"),
            lambda x: x[1].update(expected="Insurance"),
        ]
        for mutate in mutations:
            items = copy.deepcopy(self.items)
            mutate(items)
            with self.assertRaises(ValueError):
                run.validate_items(items, self.categories)

    def test_request_and_metrics(self):
        body = {
            "done": True,
            "message": {"content": "Non-Compete"},
            "prompt_eval_count": 100,
            "eval_count": 4,
            "eval_duration": 2000000000,
        }
        with patch(
            "src.run.urllib.request.urlopen",
            return_value=io.BytesIO(json.dumps(body).encode()),
        ) as request:
            row = run.call_ollama(self.items[0], self.categories)
        self.assertTrue(row["correct"])
        self.assertEqual(row["generation_tokens_per_second"], 2)
        request.assert_called_once()
        payload = json.loads(request.call_args.args[0].data)
        self.assertEqual(payload["options"], {"temperature": 0, "num_predict": 24})
        self.assertEqual(request.call_args.kwargs["timeout"], 180)
        for category in self.categories:
            self.assertIn(category, payload["messages"][1]["content"])
        second = dict(
            row, eval_count=12, eval_duration=3000000000, generation_tokens_per_second=4
        )
        summary = run.summarize([row, second], 25, 10, None)
        self.assertEqual(summary["output_tokens_per_second"], 3.2)
        self.assertEqual(summary["measured_requests_per_hour"], 720)
        self.assertIsNone(summary["self_hosted_cost_per_1000_requests_usd"])
        self.assertEqual(self_hosted_cost_per_1000(0.3, 600), 0.5)
        self.assertEqual(cost_at_traffic(5000, 0.5), 2.5)

    def test_failures_count_wrong(self):
        for exc, status in [
            (TimeoutError("late"), "timeout"),
            (urllib.error.URLError(TimeoutError("late")), "timeout"),
            (urllib.error.URLError("refused"), "error"),
        ]:
            with patch("src.run.urllib.request.urlopen", side_effect=exc):
                row = run.call_ollama(self.items[0], self.categories)
            self.assertFalse(row["correct"])
            self.assertEqual(row["status"], status)

            self.assertGreater(row["latency_ms"], 0)
        for body, status in [
            (
                {"done": True, "message": {"content": "Category: Non-Compete"}},
                "parse_error",
            ),
            ({"error": "model missing"}, "error"),
            ({"message": {"content": "Non-Compete"}}, "error"),
            ([], "error"),
        ]:
            with patch(
                "src.run.urllib.request.urlopen",
                return_value=io.BytesIO(json.dumps(body).encode()),
            ):
                row = run.call_ollama(self.items[0], self.categories)
            self.assertFalse(row["correct"])
            self.assertEqual(row["status"], status)

    def test_model_selection_and_separate_results(self):
        with tempfile.TemporaryDirectory() as directory:
            for profile, model in run.MODEL_PROFILES.items():
                body = {"done": True, "message": {"content": "Non-Compete"}}
                destination = Path(directory) / profile
                with patch(
                    "src.run.urllib.request.urlopen",
                    return_value=io.BytesIO(json.dumps(body).encode()),
                ) as request, patch(
                    "src.run.hardware_note", return_value="hardware"
                ), patch(
                    "builtins.print"
                ):
                    summary = run.run_model(
                        self.items[:1], self.categories, None, model, destination
                    )
                self.assertEqual(
                    json.loads(request.call_args.args[0].data)["model"], model
                )
                self.assertEqual(summary["model"], model)
                self.assertTrue((destination / "per_item.csv").exists())
                self.assertTrue((destination / "summary.csv").exists())
            self.assertEqual(len(list(Path(directory).glob("*/summary.csv"))), 3)


if __name__ == "__main__":
    unittest.main()
