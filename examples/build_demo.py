"""Run a real, small BM25 retriever twice and record a controlled regression.

The corpus and relevance labels are original synthetic fixtures, not customer
data. This is a mechanism demonstration, not an industry benchmark.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

from retrieval_diff import Hit, RunRecorder

DOCUMENTS = [
    {
        "id": "legacy-exports",
        "status": "legacy",
        "text": "Legacy enterprise export files remain downloadable for 90 days. "
        "Existing legacy contracts retain this export retention entitlement.",
    },
    {
        "id": "current-exports",
        "status": "active",
        "text": "Current enterprise export files remain downloadable for 30 days. "
        "Current contracts use the standard export retention entitlement.",
    },
    {
        "id": "single-sign-on",
        "status": "active",
        "text": "Single sign on lets employees log in with their company identity provider. "
        "An administrator enables single sign on under organization authentication.",
    },
    {
        "id": "refunds",
        "status": "active",
        "text": "Refunds are processed within five business days after approval. "
        "The original payment method receives the refund.",
    },
    {
        "id": "api-limits",
        "status": "active",
        "text": "API rate limits allow 120 requests per minute per organization. "
        "Excess requests receive status 429 and a Retry-After header.",
    },
    {
        "id": "password-reset",
        "status": "active",
        "text": "Password reset links expire after 15 minutes. Request a new link from the login screen.",
    },
    {
        "id": "billing",
        "status": "active",
        "text": "Monthly invoices are issued on the first business day. Billing owners can download invoices.",
    },
    {
        "id": "audit-log",
        "status": "active",
        "text": "The audit log records administrator actions. Audit entries include actor, action and timestamp.",
    },
]

QUERIES = [
    ("legacy-retention", "How long are legacy export files downloadable?", ["legacy-exports"]),
    ("sso-setup", "How do I use SSO?", ["single-sign-on"]),
    ("refund-timing", "When are refunds processed?", ["refunds"]),
    ("rate-limit", "What are API rate limits?", ["api-limits"]),
]

STOP = {
    "a",
    "an",
    "the",
    "are",
    "is",
    "for",
    "to",
    "of",
    "in",
    "on",
    "with",
    "how",
    "do",
    "i",
    "use",
    "what",
    "when",
    "long",
}


def tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP]


def search(query: str, *, expand_sso: bool) -> list[Hit]:
    terms = tokens(query)
    if expand_sso and "sso" in terms:
        terms.extend(tokens("single sign on"))
    counters = [Counter(tokens(d["text"])) for d in DOCUMENTS]
    average_length = sum(sum(c.values()) for c in counters) / len(counters)
    hits = []
    for doc, counter in zip(DOCUMENTS, counters):
        score = 0.0
        for term in set(terms):
            frequency = counter[term]
            document_frequency = sum(term in c for c in counters)
            idf = math.log(
                1 + (len(counters) - document_frequency + 0.5) / (document_frequency + 0.5)
            )
            denominator = frequency + 1.2 * (0.25 + 0.75 * sum(counter.values()) / average_length)
            score += idf * frequency * 2.2 / denominator
        if score > 0:
            hits.append(Hit(doc["id"], doc["id"] + "#0", doc["text"], round(score, 6)))
    return sorted(hits, key=lambda h: (-h.score, h.document_id))


def build_demo(output: Path, *, fixed: bool = False) -> tuple[Path, Path]:
    output.mkdir(parents=True, exist_ok=True)
    fingerprint = (
        "sha256:"
        + hashlib.sha256(
            json.dumps(DOCUMENTS, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    )
    paths = []
    for candidate in (False, True):
        exclude_legacy = candidate and not fixed
        run = RunRecorder(
            ("candidate-fixed" if fixed else "candidate") if candidate else "baseline",
            dataset_id="synthetic-policy-questions-v1",
            corpus_fingerprint=fingerprint,
            config={
                "retriever": "bm25",
                "include_legacy": not exclude_legacy,
                "expand_sso": candidate,
                "context_limit": 1,
            },
        )
        for qid, question, gold in QUERIES:
            trace = run.query(qid, question, relevant_document_ids=gold)
            found = search(question, expand_sso=candidate)
            trace.stage("search", found)
            legacy_ids = {d["id"] for d in DOCUMENTS if d["status"] == "legacy"}
            filtered = [h for h in found if not exclude_legacy or h.document_id not in legacy_ids]
            trace.stage(
                "policy_filter",
                filtered,
                dropped={
                    h.key: "status=legacy excluded by include_legacy=false"
                    for h in found
                    if h not in filtered
                },
            )
            trace.stage(
                "context",
                filtered[:1],
                dropped={h.key: "outside context_limit=1" for h in filtered[1:]},
            )
        path = output / ("candidate.json" if candidate else "baseline.json")
        run.save(path)
        paths.append(path)
    return tuple(paths)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/demo"))
    parser.add_argument("--fixed", action="store_true", help="Preserve legacy entitlements")
    args = parser.parse_args()
    for path in build_demo(args.output, fixed=args.fixed):
        print(path)
