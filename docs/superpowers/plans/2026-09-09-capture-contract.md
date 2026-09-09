# Source triage contract and queue durability

Advance issue #54 under the active full-suite request. Publish its source-skill
contract and acceptance checklist, audit Instagram against actual repository
behavior, and correct the queue durability defect found in that audit.

- Preserve existing reader gates and account approval boundaries.
- Distinguish queue capture from verified notes; keep issue #54 open for missing
  harnesses, installed workflow, checkpoint handling, and evaluated live proof.
- Flush and request filesystem sync before confirming a new queue entry. Sync
  and re-read an existing entry before a process operation treats it as safe;
  this includes a retry after failed sync left visible bytes behind.
- Reject multiline/NUL/empty entries before writing. An I/O failure must prevent
  subsequent account mutation. Do not automatically retry source mutations.
- Correct the Instagram guide's unsupported --queue flag and the claim that the
  helper deduplicates against a vault; its implementation checks urls.md only.
- Validate real local append/duplicate behavior, sync-before-confirm ordering,
  failed sync including retries, and YouTube deletion denial for new/duplicate
  entries. Run adapter and full suites, lint, generated docs, CI and review.

An fsync request does not provide universal power-loss guarantees. These helpers
remain single-orchestrator development infrastructure; no new concurrent-write,
checkpoint, live-account, installation, or platform-compliance claim is made.
