---
name: catch-up
description: Use for a FAST project orientation at the start of a session, after a break, or when switching into a repo cold — "catch me up", "where were we", "what's the state of this project", "get me up to speed", "I forgot what I was working on". Reads whatever precomputed handoff/context digest the project keeps (a docs/handoff/ tree, a root handoff.md, or CLAUDE.md/README) plus git state INLINE (no subagents) and returns current state + the single best next move.
---

# Catch Up (fast) — orient in seconds

Cold start to current state + next move, cheap. The key idea: if the project keeps a handoff or
context digest, it is **already curated** — read it, don't re-derive it. Reading a few markdown
files inline is fast and light enough for any model. No subagents on this path.

READ-ONLY: orient and propose. Don't edit, commit, or run migrations until the user picks.

## Step 0 — detect the infra first (one cheap check)

Before reading anything, check what the project actually has: a `docs/handoff/` tree, a flat
`handoff.md`/`HANDOFF.md`, or at least a `CLAUDE.md`/`AGENTS.md`/`README.md`?

- **Handoff digest exists** — fast inline path below.
- **Only CLAUDE/AGENTS/README** — still fast-path: read those plus git state, deliver the
  briefing, and offer to scaffold a handoff tree so there is a real digest next time.
- **Bare repo, nothing** — do NOT fan out subagents. Give a quick bounded briefing from git state
  alone (branch, recent commits, status), then offer scaffolding. One cheap pass, then stop.

A missing digest is a cue to offer infrastructure, never a trigger for an expensive whole-repo
scan.

## Do this inline (main thread — no fan-out)

1. **Find the digest** — freshest "current state" section of the handoff tree, or the root
   handoff file, or CLAUDE/AGENTS/README. Stop here if it is rich.
2. **Recent detail (only if thin/stale)** — newest 1-2 linked session notes plus any deferred-
   tasks file.
3. **Git state** — current branch, `git log --oneline -10`, open PRs if a remote exists,
   `git status -s`. This is what is actually moving.

## Present (scannable, action last)

```text
# Catch-up: <project>
## Snapshot      — stack · how to run + test (one line)
## In flight     — branch · uncommitted files · recent commits · open PRs
## Current state — working / blocked (on whom), straight from the digest
## Next move
1. <single best next step> — why now · rough effort
2-3. <other steps that can start now>
- Blocked on user: <approvals / secrets / external consoles>
```

End by asking which item to start, or for a goal. Do not begin implementing from catch-up — the
clear choice handed to the user IS the deliverable.
