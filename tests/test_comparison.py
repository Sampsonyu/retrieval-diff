from __future__ import annotations

import copy
import json
import math
import tempfile
import unittest
from pathlib import Path

from retrieval_diff import Hit, RunRecorder, Snapshot, ValidationError, compare
from retrieval_diff.cli import main
from retrieval_diff.report import html_report, markdown_report


def hit(doc="a", chunk="1", text="evidence", score=0.9):
    return {"document_id": doc, "chunk_id": chunk, "text": text, "score": score}


def raw(hits=None, *, gold=("a",), stages=None):
    return {
        "schema_version": 1,
        "run_id": "test",
        "dataset_id": "questions-v1",
        "corpus_fingerprint": "sha256:fixture",
        "config": {},
        "queries": [
            {
                "query_id": "q1",
                "query": "A question",
                "relevant_document_ids": list(gold) if gold is not None else None,
                "stages": stages
                if stages is not None
                else [{"name": "context", "hits": hits if hits is not None else [hit()]}],
            }
        ],
    }


def snapshot(**kwargs):
    return Snapshot.from_dict(raw(**kwargs))


class ComparisonTests(unittest.TestCase):
    def test_regression_is_per_query_even_if_mean_is_unchanged(self):
        b = raw()
        b["queries"].append(
            {
                **copy.deepcopy(b["queries"][0]),
                "query_id": "q2",
                "stages": [{"name": "context", "hits": []}],
            }
        )
        c = copy.deepcopy(b)
        c["queries"][0]["stages"][0]["hits"] = []
        c["queries"][1]["stages"][0]["hits"] = [hit()]
        r = compare(Snapshot.from_dict(b), Snapshot.from_dict(c))
        self.assertEqual(r["aggregate"]["baseline"], r["aggregate"]["candidate"])
        self.assertEqual(r["summary"]["regressed"], 1)
        self.assertEqual(r["summary"]["improved"], 1)
        self.assertEqual(r["summary"]["gate"], "fail")

    def test_chunk_id_change_does_not_change_document_recall(self):
        r = compare(snapshot(), snapshot(hits=[hit(chunk="new")]))
        self.assertEqual(r["queries"][0]["status"], "unchanged")
        self.assertEqual(r["queries"][0]["lost_documents"], [])

    def test_duplicate_document_chunks_do_not_inflate_recall(self):
        r = compare(
            snapshot(gold=("a", "b")),
            snapshot(hits=[hit(chunk="1"), hit(chunk="2")], gold=("a", "b")),
        )
        self.assertEqual(r["queries"][0]["candidate_metrics"]["document_recall"], 0.5)

    def test_mrr_uses_chunk_rank_and_only_gates_when_requested(self):
        c = snapshot(hits=[hit("b"), hit("a")])
        r = compare(snapshot(), c)
        self.assertEqual(r["summary"]["gate"], "pass")
        self.assertEqual(r["queries"][0]["status"], "declined_within_policy")
        self.assertEqual(compare(snapshot(), c, max_mrr_drop=0)["summary"]["gate"], "fail")

    def test_recall_threshold_is_absolute_and_boundary_is_allowed(self):
        b = snapshot(hits=[hit("a"), hit("b")], gold=("a", "b"))
        c = snapshot(gold=("a", "b"))
        self.assertEqual(compare(b, c, max_recall_drop=0.5)["summary"]["gate"], "pass")
        self.assertEqual(compare(b, c, max_recall_drop=0.49)["summary"]["gate"], "fail")

    def test_unlabeled_changes_are_not_called_regressions(self):
        r = compare(snapshot(gold=None), snapshot(hits=[], gold=None))
        self.assertEqual(r["summary"]["gate"], "not_evaluated")
        self.assertEqual(r["queries"][0]["status"], "unlabeled")
        self.assertEqual(r["queries"][0]["delta"], None)

    def test_attribution_uses_last_observed_transition_and_recorded_reason(self):
        stages = [
            {"name": "search", "hits": [hit()]},
            {
                "name": "filter",
                "hits": [],
                "dropped": [{"document_id": "a", "chunk_id": "1", "reason": "expired"}],
            },
            {"name": "context", "hits": []},
        ]
        d = compare(snapshot(), snapshot(stages=stages))["queries"][0]["diagnoses"][0]
        self.assertEqual((d["from_stage"], d["to_stage"]), ("search", "filter"))
        self.assertEqual(d["recorded_reasons"], ["expired"])
        self.assertTrue(d["reasons_complete"])

    def test_partial_drop_reasons_are_marked_incomplete(self):
        stages = [
            {"name": "search", "hits": [hit(), hit(chunk="2")]},
            {
                "name": "context",
                "hits": [],
                "dropped": [{"document_id": "a", "chunk_id": "1", "reason": "filtered"}],
            },
        ]
        d = compare(snapshot(), snapshot(stages=stages))["queries"][0]["diagnoses"][0]
        self.assertFalse(d["reasons_complete"])

    def test_missing_instrumentation_is_unknown(self):
        d = compare(snapshot(), snapshot(hits=[]))["queries"][0]["diagnoses"][0]
        self.assertEqual(d["kind"], "not_observed")
        self.assertNotIn("recorded_reasons", d)

    def test_top_k_loss_is_not_reported_as_filter_removal(self):
        r = compare(snapshot(), snapshot(hits=[hit("b"), hit("a")]), k=1)
        self.assertEqual(r["queries"][0]["diagnoses"][0]["kind"], "outside_top_k")

    def test_reintroduced_document_uses_last_disappearance(self):
        stages = [
            {"name": "search", "hits": [hit()]},
            {"name": "filter", "hits": []},
            {"name": "fallback", "hits": [hit()]},
            {"name": "context", "hits": []},
        ]
        d = compare(snapshot(), snapshot(stages=stages))["queries"][0]["diagnoses"][0]
        self.assertEqual(d["from_stage"], "fallback")

    def test_incomparable_runs_fail(self):
        for field, value in (("corpus_fingerprint", "other"), ("dataset_id", "other")):
            c = raw()
            c[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValidationError, field):
                compare(snapshot(), Snapshot.from_dict(c))
        for field, value in (
            ("query", "changed"),
            ("query_id", "missing"),
            ("relevant_document_ids", ["b"]),
        ):
            c = raw()
            c["queries"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValidationError):
                compare(snapshot(), Snapshot.from_dict(c))

    def test_bad_policy_fails(self):
        for kwargs in (
            {"k": 0},
            {"k": True},
            {"max_recall_drop": math.nan},
            {"max_recall_drop": -1},
            {"max_mrr_drop": math.inf},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValidationError):
                compare(snapshot(), snapshot(), **kwargs)


class ContractTests(unittest.TestCase):
    def test_invalid_contracts_fail(self):
        invalid = []
        for field, value in (
            ("schema_version", True),
            ("schema_version", 2),
            ("queries", []),
            ("config", {"bad": math.nan}),
        ):
            r = raw()
            r[field] = value
            invalid.append(r)
        r = raw()
        r["queries"].append(copy.deepcopy(r["queries"][0]))
        invalid.append(r)
        invalid.extend(
            [
                raw(hits=[hit(), hit()]),
                raw(gold=()),
                raw(hits=[hit(score=math.nan)]),
                raw(hits=[hit(score=True)]),
                raw(stages=[{"name": "search", "hits": []}]),
                raw(
                    stages=[
                        {"name": "search", "hits": [hit()]},
                        {"name": "context", "hits": [hit(text="changed")]},
                    ]
                ),
            ]
        )
        r = raw()
        r["queries"][0]["relevant_document_id"] = "typo"
        invalid.append(r)
        for r in invalid:
            with self.subTest(r=r), self.assertRaises(ValidationError):
                Snapshot.from_dict(r)

    def test_drop_reasons_cannot_reference_kept_or_unobserved_chunks(self):
        for hits in ([], [hit()]):
            with self.subTest(hits=hits), self.assertRaisesRegex(ValidationError, "drop reasons"):
                snapshot(
                    stages=[
                        {"name": "search", "hits": hits},
                        {
                            "name": "context",
                            "hits": hits,
                            "dropped": [{"document_id": "a", "chunk_id": "1", "reason": "bad"}],
                        },
                    ]
                )

    def test_recorder_round_trip_is_valid(self):
        run = RunRecorder("r1", dataset_id="d1", corpus_fingerprint="hash")
        q = run.query("q1", "Question", relevant_document_ids=["a"])
        q.stage("search", [Hit("a", "1")])
        q.stage("context", [], dropped={("a", "1"): "filtered"})
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "run.json"
            run.save(path)
            self.assertEqual(Snapshot.load(path), run.snapshot())

    def test_python_dictionary_round_trip_uses_json_arrays(self):
        original = snapshot()
        self.assertEqual(Snapshot.from_dict(original.to_dict()), original)

    def test_duplicate_json_fields_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"
            path.write_text('{"schema_version":1,"schema_version":2}')
            with self.assertRaisesRegex(ValidationError, "duplicate JSON key"):
                Snapshot.load(path)

    def test_invalid_unicode_and_oversized_numeric_scores_fail_cleanly(self):
        for value in (raw(hits=[hit(score=10**1000)]), raw(hits=[hit(text="\ud800")])):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                Snapshot.from_dict(value)


class CliAndReportTests(unittest.TestCase):
    def test_html_embeds_untrusted_text_as_data(self):
        attack = '</script><script>window.injected=true</script><img src="https://example.com">'
        b = raw(hits=[hit(text=attack)])
        r = compare(Snapshot.from_dict(b), Snapshot.from_dict(b))
        html = html_report(r)
        self.assertNotIn(attack, html)
        self.assertIn("\\u003c/script>", html)
        self.assertIn("textContent", html)
        self.assertNotIn("innerHTML", html)
        self.assertIn("connect-src 'none'", html)

    def test_markdown_escapes_user_html_and_table_separators(self):
        b = raw()
        b["queries"][0]["query_id"] = "<img>|evil\nrow"
        result = markdown_report(compare(Snapshot.from_dict(b), Snapshot.from_dict(b)))
        self.assertNotIn("<img>", result)
        self.assertIn("&lt;img&gt;\\|evil row", result)

    def test_cli_exit_codes_reports_and_no_input_clobber(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            b, c, report = root / "b.json", root / "c.json", root / "report.html"
            snapshot().save(b)
            snapshot(hits=[]).save(c)
            self.assertEqual(main(["compare", str(b), str(c), "--html", str(report)]), 1)
            self.assertTrue(report.exists())
            self.assertEqual(main(["compare", str(b), str(b)]), 0)
            self.assertEqual(main(["compare", str(b), str(c), "--html", str(b)]), 2)
            self.assertEqual(Snapshot.load(b), snapshot())
            self.assertEqual(main(["compare", str(b), str(c), "--k", "0"]), 2)
            self.assertEqual(main(["compare", str(root / "missing"), str(c)]), 2)
            self.assertEqual(main(["validate", str(b)]), 0)

    def test_require_labels_rejects_unlabeled_without_creating_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path, output = root / "run.json", root / "report.html"
            snapshot(gold=None).save(path)
            self.assertEqual(
                main(["compare", str(path), str(path), "--require-labels", "--html", str(output)]),
                2,
            )
            self.assertFalse(output.exists())

    def test_unlabeled_cli_explicitly_says_not_evaluated(self):
        import contextlib
        import io

        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "run.json"
            snapshot(gold=None).save(path)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["compare", str(path), str(path)]), 0)
            self.assertIn("NOT_EVALUATED", output.getvalue())

    def test_cli_json_and_markdown_are_consistent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "run.json"
            snapshot().save(path)
            self.assertEqual(
                main(
                    [
                        "compare",
                        str(path),
                        str(path),
                        "--json",
                        str(root / "r.json"),
                        "--markdown",
                        str(root / "r.md"),
                    ]
                ),
                0,
            )
            self.assertEqual(json.loads((root / "r.json").read_text())["summary"]["gate"], "pass")
            self.assertIn("**PASS**", (root / "r.md").read_text())


if __name__ == "__main__":
    unittest.main()
