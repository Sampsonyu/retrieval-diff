"""Instrument a real LangChain Runnable retrieval chain over pinned public docs.

The corpus is real; questions, labels, and the deliberately narrowed path filter
are authored for this controlled integration experiment. No LLM is invoked.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import re
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda
from rank_bm25 import BM25Okapi

from retrieval_diff import RunRecorder, compare
from retrieval_diff.adapters import hits_from_documents
from retrieval_diff.report import html_report, markdown_report

HERE = Path(__file__).resolve().parent
STOP = {
    "a",
    "an",
    "the",
    "is",
    "are",
    "to",
    "in",
    "of",
    "for",
    "and",
    "how",
    "do",
    "i",
    "can",
    "with",
}


def tokens(text: str) -> list[str]:
    return [word for word in re.findall(r"[a-z0-9_]+", text.lower()) if word not in STOP]


def load_corpus() -> tuple[list[Document], str, dict]:
    manifest = json.loads((HERE / "corpus/sources.json").read_text())
    documents = []
    for source in manifest["documents"]:
        data = (HERE / "corpus" / source["local_file"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != source["sha256"]:
            raise ValueError(f"Pinned source checksum mismatch: {source['local_file']}")
        # Fixed word windows make this particular experiment reproducible. They
        # are not a claim that fixed windows are best for documentation retrieval.
        words = data.decode("utf-8").split()
        for start in range(0, len(words), 90):
            documents.append(
                Document(
                    page_content=" ".join(words[start : start + 120]),
                    metadata={
                        "source": source["document_id"],
                        "chunk_id": f"words-{start}",
                        "source_url": source["url"],
                    },
                )
            )
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    return documents, "sha256:" + hashlib.sha256(canonical.encode()).hexdigest(), manifest


def build_runs(output: Path, *, fixed: bool = False) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    chunks, fingerprint, manifest = load_corpus()
    questions = json.loads((HERE / "queries.json").read_text())
    by_source = {}
    for source in manifest["documents"]:
        by_source[source["document_id"]] = (HERE / "corpus" / source["local_file"]).read_text()
    for q in questions:
        if not all(q["evidence_quote"] in by_source[doc] for doc in q["relevant_document_ids"]):
            raise ValueError(f"Evidence quote missing from labeled source: {q['query_id']}")
    bm25 = BM25Okapi([tokens(chunk.page_content) for chunk in chunks])
    dataset = (
        "fastapi-docs-v1:"
        + hashlib.sha256(json.dumps(questions, sort_keys=True).encode()).hexdigest()[:16]
    )

    def search(state: dict) -> dict:
        scores = bm25.get_scores(tokens(state["query"]))
        ranked = sorted(range(len(chunks)), key=lambda i: (-scores[i], i))
        results = [
            Document(
                page_content=chunks[i].page_content,
                metadata={**chunks[i].metadata, "retrieval_score": float(scores[i])},
            )
            for i in ranked[:12]
            if scores[i] > 0
        ]
        state["trace"].stage("bm25_search", hits_from_documents(results))
        return {**state, "documents": results}

    snapshots = []
    for candidate in (False, True):
        tutorial_only = candidate and not fixed
        run = RunRecorder(
            ("fastapi-candidate-fixed" if fixed else "fastapi-candidate")
            if candidate
            else "fastapi-baseline",
            dataset_id=dataset,
            corpus_fingerprint=fingerprint,
            config={
                "retriever": "rank-bm25/BM25Okapi",
                "framework": "LangChain RunnableLambda",
                "source_commit": manifest["commit"],
                "search_limit": 12,
                "context_limit": 3,
                "path_scope": "tutorial-only" if tutorial_only else "all-docs",
                "chunk_words": 120,
                "overlap_words": 30,
            },
        )

        def scope_filter(state: dict, tutorial_only: bool = tutorial_only) -> dict:
            before = state["documents"]
            kept = [d for d in before if not tutorial_only or "/tutorial/" in d.metadata["source"]]
            dropped = [
                d for d in before if tutorial_only and "/tutorial/" not in d.metadata["source"]
            ]
            state["trace"].stage(
                "path_scope_filter",
                hits_from_documents(kept),
                dropped={
                    (
                        d.metadata["source"],
                        d.metadata["chunk_id"],
                    ): "source outside tutorial/; path_scope=tutorial-only"
                    for d in dropped
                },
            )
            return {**state, "documents": kept}

        def context(state: dict) -> dict:
            docs = state["documents"]
            state["trace"].stage(
                "context",
                hits_from_documents(docs[:3]),
                dropped={
                    (d.metadata["source"], d.metadata["chunk_id"]): "outside context_limit=3"
                    for d in docs[3:]
                },
            )
            return {**state, "documents": docs[:3]}

        chain = RunnableLambda(search) | RunnableLambda(scope_filter) | RunnableLambda(context)
        for question in questions:
            trace = run.query(
                question["query_id"],
                question["query"],
                relevant_document_ids=question["relevant_document_ids"],
            )
            chain.invoke({"query": question["query"], "trace": trace})
        snap = run.snapshot()
        snap.save(output / ("candidate.json" if candidate else "baseline.json"))
        snapshots.append(snap)
    report = compare(*snapshots, k=3)
    (output / "report.html").write_text(html_report(report), encoding="utf-8")
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (output / "report.md").write_text(markdown_report(report))
    measurements = {
        "corpus_documents": len(manifest["documents"]),
        "chunks": len(chunks),
        "queries": len(questions),
        "source_commit": manifest["commit"],
        "corpus_fingerprint": fingerprint,
        "summary": report["summary"],
        "aggregate": report["aggregate"],
        "versions": {
            name: importlib.metadata.version(name)
            for name in ("langchain-core", "rank-bm25", "numpy")
        },
        "scope": "Controlled retrieval-layer integration on public source documents; no LLM or external user trial.",
    }
    (output / "measurements.json").write_text(json.dumps(measurements, indent=2) + "\n")
    return measurements


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/fastapi-docs"))
    parser.add_argument("--fixed", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build_runs(args.output, fixed=args.fixed), indent=2))
