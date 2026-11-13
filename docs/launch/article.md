# The source was in search results. A path filter removed it before context.

Retrieval debugging is easier when intermediate outputs are recorded. A final
context list tells us what the application retained, but it can hide where a
missing source disappeared.

To test a concrete review workflow, I built a small LangChain retrieval chain
over public FastAPI documentation and instrumented its stages with Retrieval Diff.
This article describes a deliberately introduced regression, not a production
incident or an external user's results.

## Make the comparison reproducible

The experiment uses 12 source pages from one immutable FastAPI commit. The files
are included under their MIT license, and SHA-256 checksums are verified before
each run. There is no live source download during execution.

The chain splits the pages into 144 fixed-word chunks, indexes them with BM25,
and runs eight authored questions with document-level relevance labels. Each
query records three stages:

```text
bm25_search → path_scope_filter → context
```

The search candidate limit is 12 chunks; final context is limited to three.
The code, labels, source URLs, and dependency versions are in the repository.

## Change just the source scope

The baseline allows all indexed documents. The candidate keeps only paths under
`tutorial/`. This is a plausible scope restriction for a tutorial assistant, but
it excludes the advanced WebSocket and lifespan pages.

The corpus, questions, index, and context budget stay fixed. In the captured
runs, two questions lose their relevant documents. Mean document recall@3 falls
from 1.00 to 0.75.

Those numbers describe this eight-question fixture only. They are not an
estimate of general retrieval quality.

## Inspect the stage evidence

Open the demo and select **Regressions**. For the WebSocket or lifespan question,
switch the candidate view from `context` to `bm25_search`.

The relevant document appears in search. It is absent after the next stage,
`path_scope_filter`, which recorded this reason:

```text
source outside tutorial/; path_scope=tutorial-only
```

The tool reports the observed transition and the application's removal annotation.
It does not infer a root cause from an LLM or assume scores from different models
share a common scale.

Restoring the scope returns document recall@3 to 1.00 and removes both per-query
regressions. The corrected report is available beside the failing run.

## Record actual outputs instead of reconstructing them later

The example uses `langchain_core.documents.Document` and `RunnableLambda`.
The optional adapter maps explicit source and chunk IDs to the core input model:

```python
from retrieval_diff.adapters import hits_from_documents

trace.stage("bm25_search", hits_from_documents(search_results))
trace.stage(
    "path_scope_filter", hits_from_documents(filtered_results), dropped=recorded_filter_reasons
)
trace.stage("context", hits_from_documents(context_results))
```

Stable source IDs matter. Replacing chunk IDs after re-chunking should not, by
itself, imply a relevant document vanished. Conversely, a document-level match
can hide a wrong passage. Passage correctness is outside this release's scope.

If only final context is recorded, Retrieval Diff can compare source changes;
the cause of a missing source remains unknown. Complete intermediate outputs are
necessary for stage disappearance evidence.

## Try the workflow

Interactive reports:
https://retrieval-diff-demo.sampsonyu.chatgpt.site

Source and reproduction:
https://github.com/Sampsonyu/retrieval-diff/tree/main/examples/fastapi_docs

The next validation is practical: can another engineer export a real retrieval
change without much work, and does this review reveal something useful? Setup
friction, misleading output, and overlap with existing tools are all valuable
feedback. No private source text needs to be shared.
