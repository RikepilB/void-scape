# Build Week provenance

Voidscape is a new repository with a fresh Git history, not a claim that every line was written
during OpenAI Build Week.

## Prior work imported on 2026-07-18

The initial commit ports Richard Pillaca's existing open-source `read-video` engine and skill
bundle: the probe/estimate/run CLI, frame extraction, transcription backends, consent gates,
Instagram helper, installers, demo fixture, documentation, and test suite. The import was
sanitized for a Codex-only active project surface and retained the upstream MIT attribution in
`CREDITS.md`. The component-by-component record and intentional exclusions are documented in the
[`read-video` import audit](read-video-import-audit.md).

## New Build Week work in this repository

Commits after the import are the evidence judges should score. The post-import release history
includes:

- `e531409` — rejects unapproved cloud chains before media work, scopes non-caption audio before
  transcription, rejects non-empty evidence directories, improves guided local defaults, fixes the
  privacy-proof demo setup, and adds regression tests.
- `52bc01e` — publishes the Voidscape-only landing-page identity and correct repository, Security,
  and License targets through PR #7.
- The final Build Week release — aligns scoped transcripts to the source timeline, makes dual-root
  installer failures explicit, publishes the guide/legal/community package, and records the
  reproducible judge and browser checks.

Git history and the import audit remain the source of truth. An issue, draft, or local working-tree
edit is not evidence of completed Build Week work.

Richard made the product calls: local-first operation, the explicit `inspect -> preview -> read`
discipline, separate consent for cloud transfer and model downloads, timestamp-grounded answers,
the target use cases, and the decision to defer unattended orchestration. Codex accelerated
repository reconciliation, risk analysis, implementation, test design, browser verification, and
release packaging.

## Evidence

- The import commit identifies the prior baseline explicitly.
- Every later commit contains only work performed in this repository during the Submission Period.
- GitHub issues #1–#6 track the remaining code, verification, and manual submission work.
- Select the `/feedback` session only after the post-import core changes are complete.
