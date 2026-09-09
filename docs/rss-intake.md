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

RSS GUIDs and Atom IDs remain opaque. Keys hash the feed URL and entry ID.
Without an ID, the reader uses the original link; without either, it hashes
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
for review. Duplicate/empty feed entries appear in `feed_skipped`.

The envelope is `{ok,data,error,meta}`. Exit 4 means explicit fetch approval is
missing; exit 6 reports failure without echoing source URLs or exception data.
Success always reports `analyzed: 0` and `mutates_source: false`. Captured evidence
is not a completed note checkpoint.

Remaining issue #57 work: verified note publication and dedup against analyzed
notes, `substack-ingest` and harness evaluation, explicit paywall skip records,
gated media routing, and the corresponding YouTube ingest workflow.

## Validation

On 2026-09-09, a real fetch of the RSS Advisory Board's
[public sample feed](https://www.rssboard.org/files/sample-rss-2.xml) produced a
read-only preview, then two verified captured entries with `--limit 2 --apply`.
A subsequent preview verified those two duplicates and selected the next two
entries. No linked articles, enclosures, models or account actions were invoked.
This proves public sample-feed intake, not live Substack subscriber access or
an end-to-end analyzed-note workflow.

The helper's 35 regression tests measured 100% statement and branch coverage
with `coverage.py --branch`. Coverage is scoped to `rss_capture_helper.py`;
the shared article fetcher's existing tests cover its network boundary.
