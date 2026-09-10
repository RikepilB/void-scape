# Commands and note schema

Run from the resolved Voidscape checkout. Replace every placeholder; no example
path names a private vault. Use the same selected roots throughout.

```sh
python scripts/youtube_ingest_helper.py capture "<public-url>" --root "<captures>" --limit 10 --start 1 --allow-fetch
python scripts/youtube_ingest_helper.py capture "<public-url>" --root "<captures>" --limit 10 --start 1 --allow-fetch --apply
python scripts/youtube_ingest_helper.py resume --root "<captures>" --snapshot "<returned-id>"
python scripts/youtube_ingest_helper.py resume --root "<captures>" --snapshot "<returned-id>" --apply
python scripts/youtube_ingest_helper.py retained --root "<captures>" --snapshot "<returned-id>" --notes-root "<notes>"
python scripts/youtube_read.py "<captures>" "youtube:<video-id>" "<fresh-work>" --allow-read --backend auto --tier both --timeout 1800
python scripts/triage_store.py publish "<notes>" youtube "youtube:<video-id>" Tech "<draft.md>" --capture-root "<captures>" --read-root "<completed-work>"
python scripts/triage_store.py inspect "<notes>" "<receipt-id>"
```

`--allow-fetch` is unnecessary for a single-video capture, which only normalizes
identity. `--allow-read` authorizes the actual public media fetch under local-only
transcription gates. The read helper has a two-hour maximum deadline and terminates
its owned process tree on timeout; interrupted bundles must not be marked ready.
Reusing a completed matching work directory verifies hashes and avoids re-reading.

Enumeration uses a bounded positional window of at most100 items, starting at
1..10000. A changed playlist may move items between later windows; stable video
keys deduplicate them, but the tool does not claim complete history or a stable
remote cursor. Unknown/unresolved metadata stays visible. Existing captured metadata
is immutable: `metadata_changed` reports differences without replacing evidence.

Note categories: AI, Design, Product, Jobs, Content, Startup, Hackathon, Tech,
Software_Developer, News, _Skipped. Default suggested destination is
`03_Media/Transcripts/YouTube/` under the user's selected note root.

Use exactly these five scalar frontmatter fields, matching the retained entry.
`author` and `date` remain null if unavailable; never derive them from a title.

```markdown
---
source: youtube
url: https://www.youtube.com/watch?v=<video-id>
author: null
date: null
category: Tech
---
# Evidence-based title
Source: youtube:<video-id>
Priority: **Medium** — Evidence-based reason.

## Synopsis
Summary with an explicit statement of audio/visual coverage and limitations.

## Action Items
Only supported actions, or explicitly none identified.

## Key moments
- [00:04] A grounded observation at an actual transcript/frame timestamp.

## Links
Relevant source links.

## Evidence
```

The publisher replaces the Evidence section with verified artifact references.
It checks source identity, provenance and timestamp existence, not semantic truth:
the author must still read the evidence and avoid unsupported claims.
For a skip, use category `_Skipped`, `## Reason`, an observed limitation and
`--skipped --capture-root "<captures>"`; omit `--read-root` and never call it analyzed.
Additional sanitized failure evidence can be retained with repeated `--evidence`.
