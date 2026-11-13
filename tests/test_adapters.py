import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from retrieval_diff import ValidationError
from retrieval_diff.adapters import hits_from_documents


class AdapterTests(unittest.TestCase):
    def test_preserves_rank_and_explicit_identity(self):
        documents = [
            SimpleNamespace(
                page_content="Evidence",
                metadata={
                    "source": "policy",
                    "chunk_id": "42",
                    "retrieval_score": 0.7,
                    "ignored_private_metadata": "not exported",
                },
            )
        ]
        hits = hits_from_documents(documents)
        self.assertEqual(hits[0].key, ("policy", "42"))
        self.assertEqual(hits[0].score, 0.7)
        self.assertEqual(hits[0].text, "Evidence")

    def test_supports_explicit_field_mapping(self):
        document = SimpleNamespace(page_content="Text", metadata={"doc": "a", "chunk": "b"})
        hit = hits_from_documents([document], document_id_key="doc", chunk_id_key="chunk")[0]
        self.assertEqual(hit.key, ("a", "b"))
        self.assertIsNone(hit.score)

    def test_rejects_missing_ids_invalid_scores_and_duplicate_hits(self):
        for documents in (
            [SimpleNamespace(page_content="x", metadata={"source": "a"})],
            [SimpleNamespace(page_content="x", metadata=None)],
            [
                SimpleNamespace(
                    page_content="x",
                    metadata={"source": "a", "chunk_id": "b", "retrieval_score": float("nan")},
                )
            ],
            [SimpleNamespace(page_content="x", metadata={"source": "a", "chunk_id": "b"})] * 2,
        ):
            with self.subTest(documents=documents), self.assertRaises(ValidationError):
                hits_from_documents(documents)

    def test_empty_ranked_results_are_valid(self):
        self.assertEqual(hits_from_documents([]), [])


@unittest.skipUnless(
    importlib.util.find_spec("langchain_core"), "Install public-docs example requirements"
)
class PublicDocsIntegrationTests(unittest.TestCase):
    def test_actual_langchain_chain_detects_scope_regression_and_fix(self):
        spec = importlib.util.spec_from_file_location(
            "fastapi_docs_case",
            Path(__file__).resolve().parents[1] / "examples/fastapi_docs/run.py",
        )
        case = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(case)
        with tempfile.TemporaryDirectory() as tmp:
            broken = case.build_runs(Path(tmp) / "broken")
            fixed = case.build_runs(Path(tmp) / "fixed", fixed=True)
        self.assertEqual(broken["corpus_documents"], 12)
        self.assertEqual(broken["summary"]["regressed"], 2)
        self.assertEqual(broken["aggregate"]["baseline"]["document_recall"], 1.0)
        self.assertEqual(broken["aggregate"]["candidate"]["document_recall"], 0.75)
        self.assertEqual(fixed["summary"]["gate"], "pass")
        self.assertEqual(fixed["summary"]["regressed"], 0)
