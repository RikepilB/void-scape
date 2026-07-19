# Build Week provenance

Voidscape is a new repository with a fresh Git history, not a claim that every line was written
during OpenAI Build Week.

## Prior work imported on 2026-07-18

The initial commit ports Richard Pillaca's existing open-source `read-video` engine and skill
bundle: the probe/estimate/run CLI, frame extraction, transcription backends, consent gates,
Instagram helper, installers, demo fixture, documentation, and test suite. The import was
sanitized for a Codex-only active project surface and retained the upstream MIT attribution in
`CREDITS.md`.

## New Build Week work in this repository

Commits after the import are the evidence judges should score. They cover Codex-led diagnosis,
tests and fixes for time-window transcription, safe work directories, guided local defaults,
judge installation, use-case verification, and the submission narrative/demo package.

Richard made the product calls: local-first operation, the explicit `inspect -> preview -> read`
discipline, separate consent for cloud transfer and model downloads, timestamp-grounded answers,
the target use cases, and the decision to defer unattended orchestration. Codex accelerated repo
reconciliation, risk analysis, implementation, test design, browser verification, and packaging.

## Evidence

- The import commit identifies the prior baseline explicitly.
- Every later commit contains only work performed in this repository during the Submission Period.
- `docs/handoff/` records the current work state.
- Select the `/feedback` session only after the post-import core changes are complete.
