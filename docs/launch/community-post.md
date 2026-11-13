# RAG community draft — not posted; verify the community's rules first

Suggested title: **A path filter removed sources that retrieval had already found**

I'm the maintainer of Retrieval Diff, an early open-source retrieval debugging
tool. I'm looking for feedback on the instrumentation and report workflow.

I built a controlled LangChain/BM25 example on 12 pinned FastAPI documentation
pages, split into 144 chunks. An eight-question diagnostic set has explicit
relevant-source labels.

The candidate changes just one thing: only tutorial paths pass its metadata
filter. The advanced WebSocket and lifespan sources are still returned by search,
but the filter excludes them. Document recall@3 drops from 1.00 to 0.75; the
report identifies two per-query regressions and the recorded stage where each
source disappears. Restoring scope removes both regressions.

Demo: https://retrieval-diff-demo.sampsonyu.chatgpt.site

Code, pinned sources, and reproduction steps:
https://github.com/Sampsonyu/retrieval-diff/tree/main/examples/fastapi_docs

Limits: this is an intentionally introduced regression on public documents, not
an external incident or broad benchmark. Document identity does not prove passage
correctness. Final-only logs can show changes but cannot explain missing stages.

For engineers who have dealt with retrieval regressions:

- Can you capture the intermediate stage outputs in your stack?
- Would a portable before/after report help review your changes?
- What would make this redundant with the tools you already use?
