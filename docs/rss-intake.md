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
representative paywall/media acceptance. Public YouTube ingest is implemented
separately; its independent source/harness acceptance remains pending.

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

## Resource URL provenance

New feed entries include `link_redacted`; each enclosure includes `url_redacted`.
True means the retained URL differs from its supplied source, so it must not be
replayed as though it were the original resource. Missing flags in older captures
mean unknown, not false. False only records unchanged text: public destination,
redirect, access and consent checks still apply before any follow-up read.
Original query values and credentials are not retained by these flags.
An unchanged feed compared with a pre-flag capture can report `changed` because
its parsed metadata now includes these fields. That is not proof the publisher
edited the post. The original capture and its verification marker stay intact;
no automatic rewrite or provenance backfill occurs.

## Selected public article reads

Select one retained entry before requesting additional evidence:

```powershell
python scripts/rss_resource.py ./capture rss:<capture-id>
python -m skill.scripts.voidscape inspect https://example.com/post --reader article --json
python -m skill.scripts.voidscape preview https://example.com/post --reader article --json
python scripts/rss_read.py ./capture rss:<capture-id> ./article-read --allow-fetch
python scripts/triage_store.py publish ./notes rss rss:<capture-id> Tech ./draft.md --capture-root ./capture --read-root ./article-read
```

Use the exact URL returned by resource selection, not the example URL. Selection
does no network work or writes and grants no permission. Missing/redacted URL
provenance stops follow-up; it never reconstructs a removed query. Inspect and
preview expose the public-fetch gate. Only the user's scoped public article read
authorizes `--allow-fetch`; feed capture alone does not authorize every linked page.

The read worker repeats inspect/preview, checks the source and expected article
fetch gate, and uses the existing DNS-pinned public article fetcher. It does not
use browser credentials, cloud transcription or model downloads. The parent
maps this helper's `--allow-fetch` to the guided CLI's historical `--allow-cloud`
flag only with `--reader article` and the verified `article_fetch` gate. This is
permission for the public HTTP request, not an AI upload. The parent
enforces an overall deadline (180 seconds default, 600 maximum), owns the child
process tree and verifies a hash-bound receipt before reporting ready. A repeat
run verifies existing artifacts instead of fetching again; changed artifacts stop
the run. Failed runs preserve diagnostics but do not publish a ready receipt.

An article-bound note uses `## Article Excerpt` instead of `## RSS Excerpt`, with
the same untrusted label and one verbatim quotation of at most 25 words from the
retained article body. Cite `[article 1]` in supported findings. The publisher
retains and hashes the capture, read receipt, manifest and text. Ordinary feed-only
notes still use `## RSS Excerpt`; they cannot claim an article citation. Skip notes
cannot claim a completed article read.

Coverage means fetched public text, not proof of the complete publisher article.
HTTP access denial stops the fetch; a successful response may still contain only
an excerpt or login message. Inspect the actual text, record observed access walls
as explicit skips, and never infer a paywall from short text alone. Returned feeds
are rejected as the wrong resource type. No authenticated fallback is attempted.

`rss_resource.py --resource enclosure --enclosure 1` selects a one-based audio or
video enclosure and proposes its reader/tier. It does not download or read it.
Use the separate acquisition/read workflow below for a specifically requested
enclosure. Representative live paywall/media/harness acceptance remains issue #57 work.

## Selected media enclosures

```powershell
python scripts/rss_resource.py ./capture rss:<capture-id> --resource enclosure --enclosure 1
python scripts/rss_download.py ./capture rss:<capture-id> ./enclosure --enclosure 1
python scripts/rss_download.py ./capture rss:<capture-id> ./enclosure --enclosure 1 --allow-fetch
python -m skill.scripts.voidscape inspect ./enclosure/media.mkv --reader video --json
python -m skill.scripts.voidscape preview ./enclosure/media.mkv --reader video --tier audio --backend faster-whisper --transcribe-mode fast --json
python scripts/rss_media.py ./capture rss:<capture-id> ./enclosure ./media-read --enclosure 1 --tier audio --allow-read
python scripts/triage_store.py publish ./notes rss rss:<capture-id> Tech ./draft.md --capture-root ./capture --read-root ./media-read
```

The acquisition command defaults to preview: no HTTP request or local write.
With the selected fetch approved, it downloads up to 128 MiB by default (512 MiB
maximum via `--max-bytes`) under a 300-second default deadline (1800 maximum).
Each redirect uses the existing DNS/IP-pinned public transport; HTTPS downgrade,
private destinations, missing/invalid media type, unsupported HTTP compression,
oversized or truncated bodies stop acquisition. URL query redaction still makes
an original resource unavailable. Redirect URLs are not retained because they
can contain expiring tokens. Responses must explicitly declare audio/video;
generic octet-stream responses are currently unsupported.

FFmpeg must support the `fd` protocol for both input and output. Availability is
checked before fetching; no binary is installed automatically. The worker supplies
an already-open source descriptor, enables only that input protocol and a bounded
list of media demuxers, and remuxes only the first video/audio streams into
`media.mkv`. Supported input demuxers are AAC, AVI, FLAC, Matroska/WebM, MOV/MP4,
MP3, MPEG/MPEG-TS, Ogg and WAV. Playlists such as HLS and concat are rejected.
Metadata, chapters, subtitles and attachments are not copied. Original bytes
remain in `source.bin`; both artifacts and their hashes are retained. Preview
also shows the remux size ceiling (twice the download budget plus 1 MiB) and
1 MiB remux diagnostic cap; excessive decoder logging terminates that child. This is
protocol/demuxer restriction and process deadline control, not an OS sandbox or
a guarantee against decoder vulnerabilities. See [FFmpeg fd documentation](https://ffmpeg.org/ffmpeg-protocols.html#fd).

Processing is a separate `--allow-read` action. Audio enclosures default to the
audio tier; video defaults to both. Use `--tier visual` when only frames are
requested. `rss_media.py` repeats inspect/preview/read and accepts only installed
local `faster-whisper` or `whisper-cpp` backends with no required model download;
the visual tier uses no transcription backend. Unverified adjacent transcript
sidecars are rejected. There is no cloud or model-download fallback. Read timeout
defaults to 1800 seconds, maximum 7200. Download/read children are owned by the
deadline worker. Changed or incomplete artifacts stop resume; preserve partial
work and use a fresh work directory instead of overwriting it.

Media notes use `## Key moments` instead of an RSS/Article Excerpt. Cite only
actual retained `[MM:SS]` transcript/frame labels. Include the normal Synopsis,
Key points, Action Items, Links and Evidence sections. The publisher retains the
feed capture, download receipt, original media, remux, read receipt and evidence
bundle. Its Evidence section labels the selected enclosure and normalized-media
timeline; it does not promise original broadcast timing. Existing note dedup is
still per feed entry: selecting another resource does not overwrite a prior note.

HTTP 401/403 returns sanitized `rss_access_denied` with the observed status and
no authenticated fallback. An explicit `_Skipped` note can record that denial
with its capture evidence. A denial is not proof of a paywall, and a successful
fetch is not proof of complete publisher content. Live provider variety, real
podcasts/paywalls and independent skill/harness evaluation remain incomplete.
