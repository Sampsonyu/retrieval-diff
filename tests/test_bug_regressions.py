import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path

from test_comparison import snapshot

from retrieval_diff import RunRecorder, ValidationError, compare
from retrieval_diff.cli import main
from retrieval_diff.report import html_report


class BugRegressionTests(unittest.TestCase):
    def test_invalid_api_policy_returns_validation_error(self):
        for value in (None, 10**1000):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                compare(snapshot(), snapshot(), max_recall_drop=value)

    def test_snapshot_configuration_does_not_change_with_caller_state(self):
        config = {"filter": {"enabled": False}}
        recorder = RunRecorder("run", dataset_id="set", corpus_fingerprint="hash", config=config)
        recorder.query("q", "Question").stage("context", [])
        baseline = recorder.snapshot()
        config["filter"]["enabled"] = True
        self.assertFalse(baseline.config["filter"]["enabled"])

    def test_oversized_json_integer_is_a_clean_cli_input_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "oversized.json"
            path.write_text('{"schema_version":' + "9" * 5000 + "}")
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["validate", str(path)]), 2)

    def test_report_cannot_overwrite_snapshot_through_a_hard_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / "run.json", Path(tmp) / "alias.html"
            snapshot().save(source)
            original = source.read_bytes()
            os.link(source, output)
            with (
                contextlib.redirect_stderr(io.StringIO()),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                code = main(["compare", str(source), str(source), "--html", str(output)])
            self.assertEqual(code, 2)
            self.assertEqual(source.read_bytes(), original)

    def test_optional_report_navigation_is_escaped_and_cannot_inject_script_urls(self):
        report = compare(snapshot(), snapshot())
        html = html_report(report, navigation=[("Home <safe>", "../index.html")])
        self.assertIn('href="../index.html"', html)
        self.assertIn("Home &lt;safe&gt;", html)
        for href in ("javascript:alert(1)", "//example.com", "data:text/html,x"):
            with self.subTest(href=href), self.assertRaises(ValueError):
                html_report(report, navigation=[("Unsafe", href)])


if __name__ == "__main__":
    unittest.main()
