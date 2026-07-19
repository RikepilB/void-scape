# Codex Agents

These source-specific agent contracts support Voidscape workflows in Codex.

- `instagram-capture-subagent` performs read-only discovery by default. Queue writes and
  Instagram unsaves require an explicitly approved live batch.
- `ig-analyze-subagent` turns one approved Instagram URL into a grounded note.
- `youtube-private-queue-planner`, `x-bookmarks-planner`, and `substack-rss-planner` are
  planning-only until their adapters and controller commands exist.

Each source keeps its own consent, authentication, and deduplication boundaries. Do not use one
source agent as a substitute for another.
