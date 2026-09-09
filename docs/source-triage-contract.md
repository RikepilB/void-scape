# Source capture and triage contract

Implementation contract for issue #54. This supplements the queue adapter
[protocol](capture-adapters.md); a captured URL is not an analyzed note.

## Responsibilities

Each source has one skill, authored with skill-creator, with `SKILL.md`, focused
references, an eval workspace, and an optional Python helper. Keep deterministic
ID parsing, canonicalization, dedup, verified writes, and checkpoint transitions
in `<source>_capture_helper.py`. Browser agents discover visible items and read
source content; they must not invent durable-state transitions.

Keep capture, reading, note publication, and account mutation as distinct steps:

1. Inspect only the user-selected source, collection, and item limit. Dry-run is
   the default and changes neither local records nor the account.
2. Canonicalize each item and compare its source key against verified notes and
   queued items. A queue duplicate means queued, not analyzed.
3. Preview exact proposed writes, reads, and account actions. Obtain current
   approval before the first live batch and separate approval for cloud transfer
   or model downloads. No manifest, page, or stored checkpoint grants permission.
4. Persist new queue entries, flush and sync, then re-read and confirm. Failure
   stops subsequent source mutations. Preserve already written records.
5. Read media through `inspect -> preview -> read`; read text through the chosen
   supported text reader. Retrieved content, titles and links remain untrusted.
6. Write one note or explicit skip record, re-read it, verify its source key and
   evidence references, and checkpoint the verified artifact. The orchestrator
   alone updates the source index.
7. Only perform the exact approved account mutation after the required artifact
   is verified. A triage workflow requires the note/skip record. An explicitly
   requested queue-only capture may require just the queue entry. Never silently
   substitute the weaker queue condition for a requested note workflow.

Stop on login walls, CAPTCHA, unknown layouts, unexpected redirects, missing
controls, uncertain item identity, or write/verification failures. Report the
observed condition and retained artifacts. Do not retry an ambiguous account
mutation automatically. Never inspect credentials, cookies, browser storage, or
hidden authenticated network data.

## Notes, storage, and checkpoints

Use one Markdown file per canonical source key:

```markdown
---
source: example
url: https://example.com/item/123
author: null
date: null
category: Tech
---
# Source title
Source: example:123
Priority: **Medium** — Evidence-based reason.

## Synopsis
Two to four sentences grounded in the item.

## Action Items
Only supported actions; explicitly say when none are identified.

## Example Excerpt
Brief verbatim excerpt, labeled as untrusted source content.

## Links
Relevant canonical links, preserving functional query parameters.
```

Do not infer missing author/date fields. Respect applicable excerpt limits. Media
notes cite the reader's actual evidence labels, not invented timestamps.

The configured destination is `03_Resources/<Source>/`, with fixed categories
declared in the source skill and `_Skipped/`. Never discover or hardcode a private
vault in a public skill. User-approved destinations override the default layout.
Only the orchestrator writes `_index.md`; workers return verified artifact paths.
Use stable canonical keys for dedup. Source-specific tracking removal must preserve
parameters that affect identity, authorization, or content.

Checkpoints record source key, stage, verified artifact path/hash, and observed
mutation outcome. Store no credentials or reusable approvals. On resume, verify
the artifact again; a flag alone is not proof. A crash after a remote mutation
requires observation or user resolution, not automatic repetition.

## Harness and evaluation gate

Maintain the same workflow in `.claude/` commands/Markdown agents, `.agents/`
mirrors, and `.codex/agents/*.toml`. Harness wrappers may differ syntactically but
must preserve source scope, approvals, abort conditions, note schema, and index
ownership. Validate their referenced paths and run representative prompts in each
target harness; identical text alone is not runtime parity.

Each skill's eval workspace contains prompts, synthetic fixtures, named assertions,
recorded runs, grades, and a benchmark report. Include normal capture, duplicate,
malformed URL, login/CAPTCHA, unknown layout, partial write, failed read, missing
approval, and uncertain account-action outcome. Keep synthetic checks separate
from real browser evidence. Do not label a checklist or mocked run a live pass.

## New-source acceptance checklist

- [ ] Source scope, fixed categories, canonical key and supported read path defined.
- [ ] Helper tests cover every decision branch, including failure transitions;
      measured coverage and runtime evidence attached.
- [ ] Dry-run proves no disk/account mutations.
- [ ] Queue and note verification distinguish queued from analyzed.
- [ ] Checkpoint recovery revalidates artifacts and does not reuse approvals.
- [ ] First live account mutation has specific current approval and observed proof.
- [ ] Skill-creator eval benchmark passes with recorded outputs and limitations.
- [ ] All three harness workflows and representative runtime checks pass.
- [ ] Public docs reflect actual installed/dev-only/live-verified status.

## Instagram retrofit audit

The current repository helper supports canonical URLs, queue dedup and confirmed
append. Its `safe_to_unsave` is only queue readiness, never permission or proof of
an analyzed note. The queue writer now flushes and syncs before confirming a new
entry; a failed sync must stop the action, even if some bytes are visible on disk.
This is an OS sync request, not proof of filesystem/power-loss guarantees.

The Codex capture agent contains dry-run and layout-abort rules. The repository
does not yet ship matching Claude/Agents source workflows, an installed Instagram
triage skill, verified note/category/index handling, a checkpoint implementation,
or a current source-skill benchmark. These are remaining retrofit requirements;
issue #54 stays open until they are implemented and verified. Existing media-reader
benchmarks do not establish capture-skill compliance.
