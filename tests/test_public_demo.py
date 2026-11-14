import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_comparison import hit, snapshot

from retrieval_diff import compare


class PublicDemoBuildTests(unittest.TestCase):
    def setUp(self):
        source = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location(
            "public_demo", source / "scripts/build_public_demo.py"
        )
        self.builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.builder)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "web").mkdir()
        (self.root / "web/index.html").write_text((source / "web/index.html").read_text())
        for folder, candidate in (
            ("fastapi-docs", snapshot(hits=[hit("b")])),
            ("fastapi-docs-fixed", snapshot()),
            ("demo", snapshot(hits=[])),
        ):
            target = self.root / "artifacts" / folder
            target.mkdir(parents=True)
            snapshot().save(target / "baseline.json")
            candidate.save(target / "candidate.json")
            report = compare(snapshot(), candidate, k=3)
            measurement = {
                "corpus_documents": 1,
                "chunks": 2,
                "queries": 1,
                "corpus_fingerprint": "sha256:fixture",
                "summary": report["summary"],
                "aggregate": report["aggregate"],
            }
            (target / "measurements.json").write_text(json.dumps(measurement))
            (target / "report.html").write_text("STALE COMPILED REPORT")
        corpus = self.root / "examples/fastapi_docs/corpus"
        corpus.mkdir(parents=True)
        for name in ("sources.json", "FASTAPI_LICENSE"):
            (corpus / name).write_text("fixture")
        (corpus.parent / "queries.json").write_text("[]")

    def test_rebuild_uses_snapshots_and_current_template_with_working_navigation(self):
        output = self.root / "built"
        with patch.object(self.builder, "ROOT", self.root):
            self.builder.build(output)
        html = (output / "reports/fastapi-regression.html").read_text()
        self.assertNotIn("STALE COMPILED REPORT", html)
        self.assertIn('href="../index.html"', html)
        self.assertIn('href="fastapi-fixed.html"', html)
        self.assertIn('"query_id": "q1"', html)
        self.assertTrue((output / "reports/fastapi-fixed.html").exists())

    def test_stale_measurements_are_rejected_before_publication(self):
        path = self.root / "artifacts/fastapi-docs/measurements.json"
        data = json.loads(path.read_text())
        data["summary"]["regressed"] = 99
        path.write_text(json.dumps(data))
        with (
            patch.object(self.builder, "ROOT", self.root),
            self.assertRaisesRegex(ValueError, "Measurements"),
        ):
            self.builder.build(self.root / "built")


if __name__ == "__main__":
    unittest.main()
