"""Separate observed changes, labeled regressions, and instrumentation gaps."""

from __future__ import annotations

import math
from dataclasses import asdict

from .model import Query, Snapshot, ValidationError


def _documents(query: Query, k: int) -> list[str]:
    # k counts chunks, as they occupy the application's context budget. Duplicate
    # documents cannot inflate recall; MRR uses the actual first relevant chunk rank.
    return [h.document_id for h in query.final[:k]]


def _metrics(query: Query, k: int) -> dict | None:
    if query.relevant_document_ids is None:
        return None
    gold = set(query.relevant_document_ids)
    docs = _documents(query, k)
    return {
        "document_recall": len(gold.intersection(docs)) / len(gold),
        "reciprocal_rank": next((1 / i for i, doc in enumerate(docs, 1) if doc in gold), 0.0),
    }


def _loss(query: Query, document_id: str, k: int) -> dict:
    """Describe observations, never invent a cause from scores or final-only logs."""
    final = query.final
    if document_id in {h.document_id for h in final[:k]}:
        return {"kind": "present", "detail": f"Present in context top-{k}."}
    if document_id in {h.document_id for h in final}:
        return {"kind": "outside_top_k", "detail": f"Present in context, outside top-{k}."}
    for index in range(len(query.stages) - 1, -1, -1):
        stage = query.stages[index]
        if any(h.document_id == document_id for h in stage.hits):
            after = query.stages[index + 1]
            relevant_keys = {h.key for h in stage.hits if h.document_id == document_id}
            reasons = sorted({d.reason for d in after.dropped if d.key in relevant_keys})
            complete = relevant_keys.issubset({d.key for d in after.dropped})
            return {
                "kind": "removed_between_stages",
                "from_stage": stage.name,
                "to_stage": after.name,
                "recorded_reasons": reasons,
                "reasons_complete": complete,
                "detail": f"Last observed in {stage.name}; absent from the next recorded stage, {after.name}.",
            }
    return {"kind": "not_observed", "detail": "Not present in any recorded stage; cause unknown."}


def compare(
    baseline: Snapshot,
    candidate: Snapshot,
    *,
    k: int = 5,
    max_recall_drop: float = 0.0,
    max_mrr_drop: float | None = None,
) -> dict:
    if type(k) is not int or k < 1:
        raise ValidationError("k must be a positive integer")
    for name, value in (("max_recall_drop", max_recall_drop), ("max_mrr_drop", max_mrr_drop)):
        if value is not None and (
            type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1
        ):
            raise ValidationError(f"{name} must be a finite number between 0 and 1")
    for field in ("corpus_fingerprint", "dataset_id"):
        if getattr(baseline, field) != getattr(candidate, field):
            raise ValidationError(f"{field} differs; compare runs over the same corpus and dataset")
    before = {q.query_id: q for q in baseline.queries}
    after = {q.query_id: q for q in candidate.queries}
    if before.keys() != after.keys():
        missing, extra = sorted(before.keys() - after.keys()), sorted(after.keys() - before.keys())
        raise ValidationError(f"query coverage differs: missing={missing}, added={extra}")
    results = []
    for qid, b in before.items():
        c = after[qid]
        if b.query != c.query:
            raise ValidationError(f"{qid}: query text differs")
        if (set(b.relevant_document_ids) if b.relevant_document_ids is not None else None) != (
            set(c.relevant_document_ids) if c.relevant_document_ids is not None else None
        ):
            raise ValidationError(f"{qid}: relevance labels differ")
        bm, cm = _metrics(b, k), _metrics(c, k)
        bdocs, cdocs = set(_documents(b, k)), set(_documents(c, k))
        lost, gained = sorted(bdocs - cdocs), sorted(cdocs - bdocs)
        deltas = {key: cm[key] - bm[key] for key in bm} if bm is not None else None
        violations = []
        if deltas is not None:
            if deltas["document_recall"] < -max_recall_drop - 1e-12:
                violations.append("document_recall")
            if max_mrr_drop is not None and deltas["reciprocal_rank"] < -max_mrr_drop - 1e-12:
                violations.append("reciprocal_rank")
            improved = any(v > 1e-12 for v in deltas.values())
            degraded = any(v < -1e-12 for v in deltas.values())
            status = (
                "regressed"
                if violations
                else (
                    "mixed"
                    if improved and degraded
                    else "improved"
                    if improved
                    else "declined_within_policy"
                    if degraded
                    else "unchanged"
                )
            )
        else:
            status = "unlabeled"
        targets = sorted(set(lost) | (set(c.relevant_document_ids or ()) - cdocs))
        results.append(
            {
                "query_id": qid,
                "query": b.query,
                "status": status,
                "lost_documents": lost,
                "gained_documents": gained,
                "baseline_metrics": bm,
                "candidate_metrics": cm,
                "delta": deltas,
                "violations": violations,
                "diagnoses": [{"document_id": doc, **_loss(c, doc, k)} for doc in targets],
                "baseline": asdict(b),
                "candidate": asdict(c),
            }
        )
    labeled = [r for r in results if r["baseline_metrics"] is not None]
    aggregate = {}
    for side in ("baseline", "candidate"):
        aggregate[side] = (
            {
                key: sum(r[f"{side}_metrics"][key] for r in labeled) / len(labeled)
                for key in ("document_recall", "reciprocal_rank")
            }
            if labeled
            else None
        )
    regressions = sum(r["status"] == "regressed" for r in results)
    warnings = []
    if len(labeled) != len(results):
        warnings.append(
            "Unlabeled queries show changes only; they cannot pass or fail a quality gate."
        )
    warnings.append(
        "Document-level labels test source presence, not passage correctness or answer quality."
    )
    warnings.append(
        "Stage attribution is observational. Drop reasons are supplied by the retriever, not independently verified."
    )
    return {
        "report_version": 1,
        "baseline_run_id": baseline.run_id,
        "candidate_run_id": candidate.run_id,
        "dataset_id": baseline.dataset_id,
        "corpus_fingerprint": baseline.corpus_fingerprint,
        "config": {"baseline": baseline.config, "candidate": candidate.config},
        "policy": {"k": k, "max_recall_drop": max_recall_drop, "max_mrr_drop": max_mrr_drop},
        "summary": {
            "queries": len(results),
            "labeled": len(labeled),
            "regressed": regressions,
            "improved": sum(r["status"] == "improved" for r in results),
            "changed": sum(bool(r["lost_documents"] or r["gained_documents"]) for r in results),
            "gate": "fail" if regressions else "pass" if labeled else "not_evaluated",
        },
        "aggregate": aggregate,
        "warnings": warnings,
        "queries": results,
    }
