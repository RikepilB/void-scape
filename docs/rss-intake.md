# Public RSS intake

Repository-only helper for issue #57. It captures selected feed entries as local,
untrusted evidence. It does not author notes, infer that an excerpt is complete,
fetch linked articles or enclosures, or change a source account.

```powershell
# Public feed preview: explicit fetch, no disk writes.
python scripts/rss_capture_helper.py https://publication.substack.com --root ./rss-evidence --allow-fetch --limit 10

# Capture to the reviewed destination.
python scripts/rss_capture_helper.py https://publication.substack.com --root ./rss-evidence --allow-fetch --limit 10 --apply

# Local UTF-8 feed; stable publication identity, no network.
python scripts/rss_capture_helper.py feed.xml --feed-url https://example.com/feed --root ./rss-evidence --since 2026-09-01
```

Substack publication roots resolve to `/feed`. Other inputs require an exact
public feed URL. Query-bearing, credential-bearing and fragment-bearing feed
URLs are refused rather than silently changed. Authenticated subscription feeds
are unsupported. The existing article fetcher enforces public destinations,
bounded responses and validated redirects without browser credentials or proxies.
Remote `--allow-fetch` is separate from local `--apply`.

`--limit` accepts 1–100 selected entries after verified capture deduplication.
`--since YYYY-MM-DD` is inclusive from UTC midnight. Missing, malformed or
timezone-free publication dates remain eligible with `date_filter_uncertain`.
Inputs are limited to 4 MiB and 10,000 parsed entries including skipped entries.

RSS GUIDs and Atom IDs preserve internal text, with surrounding whitespace
trimmed and blank IDs treated as missing. URL-shaped IDs with redacted components
are retained as hashes so secrets are not stored and distinct query identities
do not collapse. Keys hash the feed URL and retained entry ID.
Without an ID, the reader uses the link identity under the same rule; without either, it hashes
title, date and body. Content-derived keys change when content changes and cannot
prove publisher identity. See the [RSS specification](https://www.rssboard.org/rss-specification)
and [Atom specification](https://www.rfc-editor.org/rfc/rfc4287).

The reader prefers full content fields over summaries, separates Atom alternate
links from enclosures and retains available author metadata. HTML becomes text.
URL metadata may be redacted by the article reader; a displayed URL is evidence,
not a promise that it can fetch the same resource. Enclosures are never fetched.

`.rss-capture/<id>/entry.json` stores one selected entry under the chosen root.
`captured.json` records its hash after the entry is flushed and synced. Writers
serialize through an OS lock. Duplicates are re-read and verified; changed or
missing evidence stops the run. Interrupted captures can finish publishing
identical bytes, but never overwrite existing artifacts. Changed feed content
under an existing ID is reported as `changed`, preserving the retained version
for review. Duplicate/empty feed entries appear in `feed_skipped`, truncated to
the requested limit; `feed_skipped_total` retains the full count.

The envelope is `{ok,data,error,meta}`. Exit 4 means explicit fetch approval is
missing; exit 6 reports failure without echoing source URLs or exception data.
Success always reports `analyzed: 0` and `mutates_source: false`. Captured evidence
is not a completed note checkpoint.

The [note publisher](triage-store.md#captured-rss-notes) supports authored RSS
notes bound to verified capture evidence and canonical-key analysis lookup.
Capture dedup remains separate: controllers must consult note lookup before
authoring a retained entry. The project-scoped
[substack-ingest skill](../.agents/skills/substack-ingest/SKILL.md) coordinates this
workflow. Remaining issue #57 work includes independent harness evaluation,
complete paywall/media routing workflows and YouTube ingest.

## Resume retained entries

```powershell
python scripts/rss_capture_helper.py --list-retained --root ./rss-evidence --notes-root ./publication-notes --feed-url https://publication.substack.com --limit 10
```

This local read-only inventory revalidates captures and note lookup, returning
entries that still need notes even when a feed capture reports only duplicates.
The optional feed URL restricts selection to that publication; omitting it selects
the whole capture folder. Incomplete captures are counted without returning their
unverified bodies. Pending publication is flagged for recovery of the existing
draft/receipt. Verified skipped records stay distinct from analyzed notes.
Counts describe scanned entries, not an exhaustive history; the inventory stops
when its result limit is reached and refuses more than 10,000 directory entries.
No fetch, apply or date-filter flag is accepted in retained-inventory mode.

## Validation

On 2026-09-09, a real fetch of the RSS Advisory Board's
[public sample feed](https://www.rssboard.org/files/sample-rss-2.xml) produced a
read-only preview, then two verified captured entries with `--limit 2 --apply`.
A subsequent preview verified those two duplicates and selected the next two
entries. No linked articles, enclosures, models or account actions were invoked.
This proves public sample-feed intake, not live Substack subscriber access or
an end-to-end analyzed-note workflow.

The helper's regression tests measured 100% statement and branch coverage
with `coverage.py --branch`. Coverage is scoped to `rss_capture_helper.py`;
the shared article fetcher's existing tests cover its network boundary.
