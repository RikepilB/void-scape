# Codex Agents

These source-specific agent contracts support Voidscape workflows in Codex.

- `instagram-capture-subagent` performs read-only discovery by default. Queue writes and
  Instagram unsaves require an explicitly approved live batch.
- `ig-analyze-subagent` turns one approved Instagram URL into a grounded note.
  It receives an evidence directory, never a credential path, retains supporting
  artifacts, and returns a verified draft. The controller uses
  `scripts/triage_store.py` for publication, receipts and the index. Transient skips
  are not permanent dedup records or permission to unsave.
- `youtube-private-queue-planner`, `x-bookmarks-planner`, and `substack-rss-planner` are
  planning-only until their adapters and controller commands exist.

Each source keeps its own consent, authentication, and deduplication boundaries. Do not use one
source agent as a substitute for another.

These repository contracts do not establish an installed capture workflow or live
harness parity. See the [source-triage contract](../docs/source-triage-contract.md)
for the remaining installed-workflow and evaluation requirements.
