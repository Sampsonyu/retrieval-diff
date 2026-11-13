# A path filter removed the evidence after search had already found it

We built a small LangChain retrieval chain over pinned public FastAPI
documentation to test Retrieval Diff outside its original synthetic corpus.
The questions and the regression were deliberately authored for this experiment.
This is a reproducible integration example, not a production incident or an
external user testimonial.

## Setup

- 12 FastAPI documentation pages at an immutable source commit.
- 144 fixed-word chunks, indexed with `rank-bm25`.
- Eight project-authored questions with explicit relevant-document labels.
- LangChain `RunnableLambda` stages: search → path scope filter → context.
- Top-12 search candidates and a three-chunk context budget.

The source files, checksums, license, labels, chain code, and exact dependency
pins are in [examples/fastapi_docs](../examples/fastapi_docs/README.md).

## The controlled change

The baseline permits all indexed documentation. The candidate permits only paths
containing `/tutorial/`, a plausible scope restriction when building a tutorial
assistant. This deliberately excludes pages under `/advanced/` while leaving the
search index and search scores unchanged.

## What the execution showed

| Measurement | Baseline | Narrowed scope | Restored scope |
| --- | ---: | ---: | ---: |
| Document recall@3 across eight questions | 1.00 | 0.75 | 1.00 |
| Per-query regressions against baseline | — | 2 | 0 |

The WebSocket and application-lifespan questions lost their relevant sources.
For both questions, the source appeared in `bm25_search` and disappeared at
`path_scope_filter`. The chain recorded the reason:

```text
source outside tutorial/; path_scope=tutorial-only
```

This identifies an observed loss between recorded stages. The explanation comes
from the filter annotation; the tool did not infer it from an LLM or from scores.
Restoring the source scope removed the two regressions without changing retrieval.

## Why the report helps

Looking only at final context leaves several possible explanations: search,
filtering, ranking, or context truncation. The recorded funnel distinguishes the
search results from the filtering result, and a reviewer can inspect both runs
without installing the retrieval application.

## What this does not establish

The small question set is intentionally diagnostic. Its scores are not a broad
benchmark, a statistical estimate, or evidence of production readiness. A matching
source document may contain an irrelevant passage. No generated answers are scored.
An external engineer still needs to validate integration friction and usefulness
on their own application.

## Try it

```sh
python -m pip install -e . -r examples/fastapi_docs/requirements.txt
python examples/fastapi_docs/run.py
python examples/fastapi_docs/run.py --fixed --output artifacts/fastapi-docs-fixed
```

The core comparison remains offline and dependency-free. These framework and
retriever packages are optional dependencies of this example only.
