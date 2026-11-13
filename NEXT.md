# Continuation

This track builds an original, English-only open-source product for Sampsonyu.
Upstream community contributions are managed in a separate chat. The goal is a
useful developer product with verifiable technical depth and eventual repeat
users, not a collection of tutorials or artificial activity.

## Current project

Retrieval Diff: compare matching RAG retrieval runs, identify per-query source
regressions, locate the last recorded stage containing missing evidence, and
export a portable interactive report. See README and docs/project-selection.md.

The first implementation, documentation, tests, demo, screenshots, and packaging
are complete locally. Current validation is in docs/validation.md. No real-world
adoption or production-readiness claim is authorized by this evidence.

## Repository and validation

Repository: https://github.com/Sampsonyu/retrieval-diff.
The initial owner-created repository was verified empty before the first push.
GitHub Actions tests Python 3.10, 3.12, and 3.13, builds distributions, and runs
Chromium report checks. Consult the workflow runs for hosted validation results;
docs/validation.md describes the checks completed in the development environment.

## Next product milestone

The public-document LangChain example and public interactive demo are complete.
See examples/fastapi_docs/README.md, docs/case-study.md, and web/README.md for
reproduction and hosting identity. Launch materials in docs/launch are drafts,
not sent messages. No external trial or adoption is claimed.

Next, obtain independent trial feedback on setup friction and usefulness. External
platform posts and invitations require a specific user instruction and known
channel/account; do not infer posting authorization from drafting authorization.
Preserve the distinction between observation, labeled quality, and unknown causes.
All repository-facing content stays in English.
