# Why this first project

Decision date: 2026-11-13. Working name: **Retrieval Diff**.

## User and job

An engineer changes retrieval configuration and wants to know which previously
supported questions lost relevant sources, and where in the recorded retrieval
pipeline those sources disappeared. The output should be usable during code
review without migrating to another retrieval framework.

## Evidence examined

- [RAGFlow issue #20148](https://github.com/infiniflow/ragflow/issues/20148):
  requests visibility into threshold-dropped chunks and a candidate-to-context
  funnel. It includes an upstream implementation proposal. This is evidence of
  a debugging problem, not evidence that its author wants our separate tool.
- [SPANCHOR](https://github.com/Mukeshram-07/spanchor): documents source-span
  evaluation, baseline/candidate comparisons, framework adapters, and CI gates.
  This substantially overlaps generic retrieval regression testing.
- [retrieval-lens](https://github.com/Vbj1808/retrieval-lens): describes local
  retrieval recording and source-level diff through MCP.
- [RAG-Visualizer](https://github.com/jvorndran/RAG-Visualizer): documents local
  inspection of parsing, chunking, embeddings, and retrieval configurations.

These are primary-source feature descriptions inspected during selection, not a
complete code audit or an exhaustive market survey. Competitors may evolve.

## Chosen wedge

**Recorded-stage disappearance evidence in a portable baseline/candidate review
report**, with strict coverage checks and clear boundaries around unknown causes.
The implementation is independently written; no competitor source code was
copied. The product does not claim to invent retrieval evaluation or to be the
first tool with these features.

| Criterion | Assessment |
| --- | --- |
| Concrete utility | Helps investigate a specific retrieval change using observed data |
| Feasible first version | SDK, input contract, comparator, report, and CI exit code |
| Career relevance | IR metrics, data contracts, instrumentation, testing, API and UX tradeoffs |
| Adoption friction | Local install, no model key or service, but stage capture still requires integration |
| Differentiation | Plausible combination and workflow; willingness to switch remains unvalidated |
| Maintenance scope | Python standard-library core and a static browser report |

## Alternatives considered

- A broad agent fault-testing framework has many near-neighbor projects and a
  larger integration burden. It offers no demonstrated advantage for this first
  release.
- PDF table comparison is useful but robust extraction and table alignment need
  a document-specific validation corpus. We lack that evidence today.
- An agent trace-to-test generator risks confusing observed model behavior with
  stable expected behavior. It needs a narrower contract before implementation.

## What must validate the decision

1. An engineer can export actual runs without changing retrieval decisions.
2. The report identifies a concrete issue that is hard to see from final-only
   results or aggregate metrics.
3. A fresh user can install the project and understand the report from the README.
4. At least several independent users find it worth using again.

No user interviews, external adoption, stars, downloads, or hiring outcomes are
claimed. The synthetic example validates the mechanism only. If people cannot
capture the intermediate stages or existing tools already solve their workflow
well, narrow the integration or reconsider the project before expanding scope.
