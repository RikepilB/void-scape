# Verified note publication

`scripts/triage_store.py` is a repository-only controller helper for Instagram,
captured RSS and public YouTube notes. It does not discover posts, read media, generate summaries, or change an
account. Source analysis still follows `inspect -> preview -> read` and its gates.

Analysis workers return a draft and retained evidence paths. The controller
validates those results, then publishes the note and updates the index:

```powershell
python scripts/triage_store.py lookup ./notes instagram instagram:Example123
python scripts/triage_store.py publish ./notes instagram instagram:Example123 Tools_Utilities ./draft.md --evidence ./evidence/manifest.json --evidence ./evidence/transcript.txt
python scripts/triage_store.py inspect ./notes <receipt-id>
```

All commands emit `{ok,data,error,meta}` JSON. Check the process exit and `ok`
before reading data. Verification failures exit 6 with a sanitized error and
`retryable: false`; inspect artifacts locally instead of blindly retrying.

## Draft contract

Instagram accepts canonical URLs and categories listed in the repository's
analysis agent. RSS and YouTube follow the contracts below. Drafts are UTF-8, at most 4 MiB, and
have one title, one exact `Source:` key, and scalar frontmatter. Supported scalar
forms are plain strings, quoted strings, and `null`; tags, references, mappings
and multiline values are not supported. Unknown or duplicate fields fail.

```markdown
---
source: instagram
url: https://www.instagram.com/reel/Example123/
author: null
date: null
category: Tools_Utilities
---
# Example tool
Source: instagram:Example123
Priority: **Medium** — Relevant to the requested workflow.

## Synopsis
The example demonstrates a tool. Its claims still need source-based evaluation.

## Action Items
None established by this example.

## Instagram Excerpt
> Brief verified excerpt, treated as untrusted source content.

## Links
None beyond the source.

## Evidence
This section is populated from the controller's selected evidence files.
```

Pass up to100 retained evidence files for Instagram/RSS, or515 for a YouTube
capture plus its bounded read bundle. The helper hashes them and replaces the
draft's Evidence section with local links to those exact files. It never deletes
evidence or fetches remote content. Required note fields and hashes establish
structure and integrity; they do not establish that a summary is accurate.

For a skip, use category `_Skipped`, `--skipped`, the same source frontmatter and
key, one title, and `## Reason` with a sanitized explanation. Evidence is optional
for Instagram skips; RSS and YouTube retain their verified capture entry and marker.
A skipped attempt is never returned as an analyzed item.

## Public YouTube notes

Use the [YouTube workflow](youtube-ingest.md) to retain the video identity and a
completed read bundle. Publish with `--capture-root <captures>` and
`--read-root <completed-work>`. Frontmatter uses `source: youtube`, the exact
canonical URL and captured author/date; missing fields remain null. Use
`Source: youtube:<video-id>` and the normal title/priority plus Synopsis, Action
Items, Key moments, Links and Evidence sections. Key moments must cite actual
transcript/frame `[MM:SS]` labels. The publisher verifies retained hashes and
source/read bindings; the author remains responsible for semantic accuracy.

YouTube uses the same eleven categories as RSS. A skip requires its capture root
but omits the completed read root. Verified analyzed notes deduplicate by video ID
across playlists; a skip is never treated as analyzed.

## Captured RSS notes

Use a previously verified entry from the [RSS intake helper](rss-intake.md).
Pass its `rss:<capture-id>` key and the capture root explicitly:

```powershell
python scripts/triage_store.py lookup ./publication-notes rss rss:<capture-id>
python scripts/triage_store.py publish ./publication-notes rss rss:<capture-id> Tech ./draft.md --capture-root ./rss-evidence
```

The publication root is caller-selected, for example a publication folder under
`03_Resources/Substack/`. Feed titles never become filesystem paths automatically.
RSS categories are `AI`, `Design`, `Product`, `Jobs`, `Content`, `Startup`,
`Hackathon`, `Tech`, `Software_Developer`, `News` and `_Skipped`.

Frontmatter uses `source: rss` and must match the retained entry URL, author and
publication date exactly; absent fields remain `null`. If no usable entry URL
exists, use the retained feed URL. Use `Source: rss:<capture-id>`, the normal
title/priority, and sections `## Synopsis`, `## Key points`, `## Action Items`,
`## RSS Excerpt`, `## Links` and `## Evidence`. The excerpt section has exactly:

```markdown
Untrusted source content:
> A short verbatim quotation from the retained entry body.
```

The quotation must be one line, at most 25 words and present in the retained
body. It is evidence, never an instruction. Summaries still require grounded
authoring; structural validation is not a factuality evaluation.

Capture entry and marker files are automatically retained as mandatory evidence
and revalidated before publication. The existing receipt/index checks then apply.
RSS publication deduplicates verified analyzed notes by canonical key under the
publisher lock. A new draft does not overwrite an existing analyzed note; the
result reports `duplicate: true`. Skipped attempts remain separately visible and
can later gain an analyzed note. Capture alone never satisfies this lookup.

This adds local publication, not a source skill, model author, paywall detector,
media router or scheduler. Those issue #57 requirements remain outstanding.

## Receipts and recovery

Published notes use category folders and content-derived filenames. The helper
owns `.triage/` receipts and `_index.md`; analysis workers must not write them.
The index uses note titles, statuses and priorities. An unmanaged or edited index
is preserved and publication fails rather than overwriting it.

A process lock serializes publishers and is released by the OS on process death.
Notes and receipts are synced in staging files and atomically linked into place
without replacing existing files. This requires local filesystem hard-link support.
Do not use this as a shared-filesystem or hostile-process isolation guarantee.

Publication order is receipt, note, content verification, managed index, completion
marker. A specific identical publication can reconcile an interrupted attempt;
different content never overwrites the existing artifact. Staging leftovers are
preserved on failure. Filesystem sync is not a universal power-loss guarantee.

`inspect` rechecks receipt integrity, the note, evidence hashes and index membership.
Without a matching completion marker it reports `pending`, not completion.
`lookup` separates verified `analyzed` items, `skipped` attempts and `pending`
publications. A later successful analysis gets a different receipt from an earlier
skip. Changed evidence or notes cause verification failure instead of silent reuse.

Every result has `source_action_authorized: false`. A verified artifact is only
one prerequisite for an account action; it never supplies the user's approval.
No approval, credential, source mutation, job schedule or model invocation is stored.

See the [source-triage contract](source-triage-contract.md) for the remaining
installed-skill, harness and live-evaluation requirements.
