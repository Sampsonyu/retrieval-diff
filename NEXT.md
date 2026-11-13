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

## Publishing blocker

Target account verified as Sampsonyu, ID 18622329. Target repository:
`Sampsonyu/retrieval-diff`. The account connector and gh use the expected identity.

- `gh repo create ...` returned GraphQL `Resource not accessible by integration`.
- `POST /user/repos` returned HTTP 403 `Resource not accessible by integration`.
- Cloud browser initialization failed with `the gaas-browser node_repl sandbox
  cannot be disabled`. No browser action or repository creation succeeded.
- The user has been asked to create an empty Public repository without an initial
  README and reply when ready. No push has occurred. Do not claim a published URL.

When the repository exists: verify the owner/name and that no unrelated content
will be overwritten, configure origin, push the existing main branch, and inspect
CI. Do not force-push over user changes. The user has already asked us to choose
and implement this first original project; no need to re-ask which project.

## Next product milestone

Validate recording against one actual RAG application using a public or
permissioned corpus. Measure setup friction and whether the stage report reveals
a useful issue. Add integrations or scale features only when evidence supports
the work. Preserve the distinction between observation, labeled quality, and
unknown causes. All repository-facing content stays in English.
