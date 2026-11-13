"""Small instrumentation API; it records your retriever without executing it."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict
from pathlib import Path

from .model import Hit, Snapshot


class QueryRecorder:
    def __init__(self, raw: dict):
        self._raw = raw

    def stage(
        self,
        name: str,
        hits: Iterable[Hit],
        *,
        dropped: Mapping[tuple[str, str], str] | None = None,
    ) -> QueryRecorder:
        self._raw["stages"].append(
            {
                "name": name,
                "hits": [asdict(hit) for hit in hits],
                "dropped": [
                    {"document_id": key[0], "chunk_id": key[1], "reason": reason}
                    for key, reason in (dropped or {}).items()
                ],
            }
        )
        return self


class RunRecorder:
    def __init__(
        self, run_id: str, *, dataset_id: str, corpus_fingerprint: str, config: dict | None = None
    ):
        self._raw = {
            "schema_version": 1,
            "run_id": run_id,
            "dataset_id": dataset_id,
            "corpus_fingerprint": corpus_fingerprint,
            "config": config or {},
            "queries": [],
        }

    def query(
        self, query_id: str, query: str, *, relevant_document_ids: Iterable[str] | None = None
    ) -> QueryRecorder:
        raw = {
            "query_id": query_id,
            "query": query,
            "stages": [],
            "relevant_document_ids": (
                list(relevant_document_ids) if relevant_document_ids is not None else None
            ),
        }
        self._raw["queries"].append(raw)
        return QueryRecorder(raw)

    def snapshot(self) -> Snapshot:
        return Snapshot.from_dict(self._raw)

    def save(self, path: str | Path) -> None:
        self.snapshot().save(path)
