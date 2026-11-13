# First-version validation

Date: 2026-11-13. Local environment: Linux, CPython 3.12.14.

## Verified

- **26 automated tests pass.** Coverage includes per-query regressions hidden by
  unchanged means, stable document IDs across chunk changes, duplicate-source
  handling, optional rank gates, policy boundaries, unknown causes, partial
  removal reasons, reintroduced sources, query/corpus/label mismatch, malformed
  inputs, serialization round trips, CLI exit codes, and report escaping.
- **Chromium checks pass.** Query filters, search, no-results state, stage
  selection, mobile overflow, and untrusted closing-script text were exercised.
  No outbound HTTP(S) requests were observed. Generated HTML was rendered with
  Playwright `set_content`; the managed browser blocks `file://` navigation.
- **The controlled BM25 demo reproduces the intended failure.** Baseline and
  candidate mean document recall@1 are both 0.75; one query improves and one
  regresses. The missing entitlement source disappears at `policy_filter`.
- **The corrected configuration passes.** Preserving legacy entitlements removes
  the regression while retaining the acronym-expansion improvement.
- Ruff lint/format checks pass. Source and wheel distributions build. The wheel
  includes the HTML template and was installed into a separate virtual environment
  to render a report from outside the checkout. It has no runtime dependencies.

## Not established

- External users, repeated adoption, stars, forks, or hiring outcomes.
- Integration with a production application or a particular retrieval framework.
- Correctness of document relevance labels or instrumentation supplied by callers.
- Passage relevance, answer correctness, or causal model attribution.
- Large-trace performance, statistical significance, or changed-corpus evaluation.
- Python 3.10/3.13 execution or GitHub-hosted CI results: the matrix is configured
  but has not run while repository creation is blocked by account permissions.

The evidence supports a working first version and a reproducible debugging
mechanism. It does not establish product-market fit or production maturity.
