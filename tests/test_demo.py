"""Exercise actual retrieval and filtering, including the corrected configuration."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

from retrieval_diff import Snapshot, compare


class DemoTests(unittest.TestCase):
    def test_retrieval_regression_then_fix(self):
        spec = importlib.util.spec_from_file_location(
            "build_demo", Path(__file__).resolve().parents[1] / "examples/build_demo.py"
        )
        demo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(demo)
        with tempfile.TemporaryDirectory() as temp:
            for fixed in (False, True):
                b, c = demo.build_demo(Path(temp) / str(fixed), fixed=fixed)
                report = compare(Snapshot.load(b), Snapshot.load(c), k=1)
                self.assertEqual(report["summary"]["regressed"], 0 if fixed else 1)
                self.assertEqual(report["summary"]["improved"], 1)
                self.assertEqual(report["summary"]["gate"], "pass" if fixed else "fail")
                if not fixed:
                    self.assertEqual(report["aggregate"]["baseline"]["document_recall"], 0.75)
                    self.assertEqual(report["aggregate"]["candidate"]["document_recall"], 0.75)
                    query = next(
                        q for q in report["queries"] if q["query_id"] == "legacy-retention"
                    )
                    self.assertEqual(query["diagnoses"][0]["to_stage"], "policy_filter")
