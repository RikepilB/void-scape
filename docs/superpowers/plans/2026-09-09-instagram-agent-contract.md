# Correct the Instagram analysis contract

Issue54 retrofit audit found stale instructions in the existing Codex agent:
credential-path handoff, unconditional evidence deletion, substring dedup and
permanent treatment of transient skips. Correct these before checkpoint automation.

- Replace the credential-path input with a controller-selected evidence directory.
- Keep inspect/preview/read JSON and explicit fail-closed flags; require read output
  validation as well. Partial and stopped results are not completed analyses.
- Retain source evidence and verify written note paths and exact source identity.
- Skip records describe attempts, not permanent completion or unsave authorization.
- Add source frontmatter, excerpt, links and retained evidence to the note template.
- Preserve existing fixed categories, index ownership and current approval gates.
- Capture only the named user-selected collection; reject missing/ambiguous scope
  and malformed helper results. Queue readiness never grants account permission.

Validate TOML syntax, prompt-regression guards and the full repository suite. These
checks protect the instruction contract; they are not a live harness benchmark,
an installed workflow, or implementation of the remaining deterministic checkpoint
and note-publishing helper. Keep issue54 open.
