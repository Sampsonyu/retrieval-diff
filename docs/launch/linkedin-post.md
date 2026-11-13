# LinkedIn draft — not posted

I've been building Retrieval Diff, an open-source tool for reviewing retrieval
changes in RAG applications.

For a reproducible integration test, I connected it to a LangChain retrieval
chain over 12 pinned FastAPI documentation pages: 144 chunks and eight
hand-labeled questions.

I deliberately narrowed the candidate's path filter to tutorial pages. Two
questions lost their relevant sources, even though search had already found
them. The report showed the sources disappearing between search and the path
filter. Restoring the scope removed both regressions.

This is a controlled public-document experiment, not a customer's production
incident. It measures source presence, not generated-answer accuracy.

You can explore the failing and corrected reports without installing anything:
https://retrieval-diff-demo.sampsonyu.chatgpt.site

Source and reproduction steps:
https://github.com/Sampsonyu/retrieval-diff

If you work on retrieval filters, reranking, or context assembly, I'd value a
small trial: can you record your stages, and does the report reveal something
your final-result logs miss?
