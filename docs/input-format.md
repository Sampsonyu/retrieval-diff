# Snapshot contract, version 1

A snapshot records one run over a fixed query set and fixed source corpus. The
format is UTF-8 JSON. Unknown fields, duplicate object keys, duplicate query IDs,
duplicate stages, duplicate hits within a stage, non-finite scores, and malformed
drop annotations are rejected. Hit identity is `(document_id, chunk_id)`.

```json
{
  "schema_version": 1,
  "run_id": "baseline",
  "dataset_id": "support-questions-v1",
  "corpus_fingerprint": "sha256:HASH_OF_CANONICAL_CONTENT",
  "config": {"threshold": 0.6},
  "queries": [
    {
      "query_id": "q1",
      "query": "When are refunds processed?",
      "relevant_document_ids": ["refund-policy"],
      "stages": [
        {
          "name": "search",
          "hits": [
            {"document_id": "refund-policy", "chunk_id": "42", "text": "Five business days.", "score": 0.7}
          ]
        },
        {
          "name": "context",
          "hits": [],
          "dropped": [
            {"document_id": "refund-policy", "chunk_id": "42", "reason": "blocked by status filter"}
          ]
        }
      ]
    }
  ]
}
```

## Required fields

- Snapshot: `schema_version` (integer 1), `run_id`, `dataset_id`,
  `corpus_fingerprint`, nonempty `queries`. Optional `config` is a JSON object.
- Query: nonempty `query_id`, `query`, `stages`.
- Stage: nonempty `name`, `hits` in ranked order. Last stage must be `context`.
- Hit: nonempty `document_id`, `chunk_id`; optional `text` defaults to empty,
  optional `score` defaults to null. Text for a hit identity cannot change between
  recorded stages in the same query.
- Optional `dropped`: `document_id`, `chunk_id`, and nonempty `reason` for chunks
  that were present in the previous recorded stage and are absent in this one.
  It is valid to record only some reasons; reports mark incomplete annotations.

Stages may introduce new hits, for example a fallback retriever or parent lookup.
Each stage must record the complete actual output, not a sample. Intermediate
stages are optional. With only `context`, missing sources have unknown causes.

`relevant_document_ids` is either omitted/null (unlabeled) or a nonempty unique
list of document IDs. An empty list is rejected because it cannot distinguish an
unlabeled question from a deliberate no-answer test. No-answer tests are not
supported in this release. A relevant source may be absent from every result.

## Comparable runs

Baseline and candidate must have identical dataset/corpus identifiers, exact query
coverage, query text for each ID, and relevance-label sets. Configurations and
recorded stage names may differ. The report does not subtract scores across runs:
an embedding cosine score and a reranker logit do not share a scale.

Compute the corpus fingerprint from canonical document IDs, text, and metadata
used for filtering, sorted deterministically. Preserve document IDs across
chunking changes. The caller is responsible for these identity guarantees.

## Report contract

JSON reports include `report_version: 1`, `summary`, `aggregate`, `policy`,
configuration, warnings, and per-query deltas, diagnoses, and recorded snapshots.
This first version intentionally exposes observations rather than inferred root
causes. HTML and Markdown render the same comparison object.
