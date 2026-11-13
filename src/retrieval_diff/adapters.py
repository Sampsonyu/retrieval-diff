"""Explicit field mapping for LangChain-style documents, without framework imports."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Protocol

from .model import Hit, ValidationError


class DocumentLike(Protocol):
    page_content: str
    metadata: dict


def hits_from_documents(
    documents: Iterable[DocumentLike],
    *,
    document_id_key: str = "source",
    chunk_id_key: str = "chunk_id",
    score_key: str = "retrieval_score",
) -> list[Hit]:
    """Convert ranked documents; require stable source and chunk IDs explicitly.

    No text hashing, inferred IDs, network calls, or LangChain imports occur here.
    The input order is preserved. Extra metadata is not copied to the report.
    """
    hits = []
    for index, document in enumerate(documents):
        metadata = getattr(document, "metadata", None)
        if not isinstance(metadata, Mapping):
            raise ValidationError(f"documents[{index}].metadata: expected a mapping")
        for key in (document_id_key, chunk_id_key):
            if key not in metadata:
                raise ValidationError(f"documents[{index}].metadata: missing explicit {key!r}")
        hits.append(
            Hit.parse(
                {
                    "document_id": metadata[document_id_key],
                    "chunk_id": metadata[chunk_id_key],
                    "text": getattr(document, "page_content", None),
                    "score": metadata.get(score_key),
                },
                f"documents[{index}]",
            )
        )
    if len({hit.key for hit in hits}) != len(hits):
        raise ValidationError("documents: duplicate source/chunk identifiers")
    return hits
