# First-version validation

## Public-document integration update

The optional LangChain/BM25 example executes against 12 pinned, licensed FastAPI
source documents (144 chunks, eight authored questions). A deliberately narrowed
path filter causes two per-query source regressions; restoring scope removes
both. The expanded local suite passes 31 tests with the optional example
dependencies installed. The framework-free suite skips that integration test.

The public demo is deployed at https://retrieval-diff-demo.sampsonyu.chatgpt.site.
Static internal links and measurement substitutions were checked. The native
Sites service confirmed publication with public access. The managed preview relay
failed to start, so hosted-page browser QA is not claimed. This is not evidence
of external users or a production incident.
An additional direct HTTP probe from the Cloud executor received Cloudflare
403/1010; the Sites control plane still confirms an active public deployment.
Anonymous browser access from an independent device has not been verified here.

## Original core validation

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
- This document records local Python 3.12 validation. For Python 3.10/3.13 and
  GitHub-hosted browser/build results, see the repository's
  [workflow runs](https://github.com/Sampsonyu/retrieval-diff/actions/workflows/ci.yml).

The evidence supports a working first version and a reproducible debugging
mechanism. It does not establish product-market fit or production maturity.
