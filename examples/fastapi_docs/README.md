# LangChain retrieval on pinned FastAPI documentation

This example records a real LangChain `RunnableLambda` retrieval chain using
`rank-bm25` over 12 pinned public FastAPI documentation files. It is a controlled
integration experiment created for this project, not an external customer's
incident, production application, or generated-answer benchmark. No LLM is called.

## Reproduce

From the repository root, with Python 3.12 or newer:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e . -r examples/fastapi_docs/requirements.txt
python examples/fastapi_docs/run.py
python examples/fastapi_docs/run.py --fixed --output artifacts/fastapi-docs-fixed
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` instead.

Open `artifacts/fastapi-docs/report.html` and select **Regressions**. For either
failed query, switch the candidate stage from `context` to `bm25_search`. The
relevant source was retrieved, then excluded by `path_scope_filter`.

The experiment runner writes measurements and reports and exits 0 on successful
execution. To exercise the CLI gate independently:

```sh
retrieval-diff compare artifacts/fastapi-docs/baseline.json \
  artifacts/fastapi-docs/candidate.json --k 3 --require-labels
```

This deliberately exits **1**. The equivalent comparison in
`artifacts/fastapi-docs-fixed/` exits **0**.

## What changed

All runs use the same corpus, question set, BM25 index, 120-word chunk windows
with 30-word overlap, top-12 search results, and three-chunk context budget.
Only the candidate's metadata scope changes to paths containing `/tutorial/`.
That scope excludes the advanced WebSocket and lifespan documentation. The
fixed candidate restores the original scope.

Measured on this exact fixture: **12 source documents, 144 chunks, 8 questions**.
Document recall@3 changes from **1.00 to 0.75**, with **2 per-query regressions**.
The fixed run returns to **1.00**, with **0 regressions**. These are fixture
measurements, not estimates of general RAG quality or product adoption.

## Provenance and limitations

- Source repository: [fastapi/fastapi](https://github.com/fastapi/fastapi), commit
  `5758a9c8347d911444dca97a55b708cc4a8de4f8`.
- `corpus/sources.json` records immutable source URLs and SHA-256 checksums.
  Checksums are verified before every run. No runtime document download occurs.
- FastAPI documentation is distributed here under its [MIT license](corpus/FASTAPI_LICENSE),
  copyright Sebastián Ramírez. No FastAPI affiliation or endorsement is implied.
- `queries.json` contains project-authored questions, document-level labels, and
  supporting source quotations. They are a small hand-selected diagnostic set.
- The adapter requires explicit stable source/chunk IDs. It does not infer them
  or copy unrelated metadata into reports.
- This checks retrieval instrumentation and source presence, not answer accuracy,
  passage correctness, embedding performance, or third-party adoption.
