# RSS enclosure verification

Branch: `codex/rss-enclosure-read`, issue #57 continuation.

## Real public fetch and visual evidence

A synthetic feed entry selected the MP4 linked by the official
[MDN video example](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/video).
The actual anonymous request, bounded download worker, descriptor-only remux,
local inspect/preview and visual read completed. The normalized clip measured
5.06 seconds,960x540. Ten frames were retained. Frames1,5,10 were inspected:
a mostly closed red bud at00:00, opening petals at00:02, an open flower at00:04.
No audio claim was made. A local note with those labels published and its receipt
revalidated. This was synthetic feed selection, not a real MDN feed.

## Controlled speech and local transcription

Windows SAPI generated three synthetic sentences over a solid blue video:
identifying a test recording, a workshop beginning Friday, and bringing a laptop
and reviewing a checklist. The fixture transport copied this locally generated
media; no request to its example.com identity occurred. Descriptor remux and the
real local reader ran afterward. Inspect measured13.95 seconds; preview reported
the faster-whisper small model cached with all cloud/download/install gates false.

Local ASR retained all three sentences at00:00,00:02,00:05,131 characters total.
The full transcript and one deduplicated blue frame were inspected. A second note
published and revalidated. This proves the controlled local speech/frame flow;
it is not a real podcast, multilingual/noisy-speech benchmark or independent agent
evaluation. No new model, cloud API, browser account or external note destination.

## Mechanism checks

Tests cover preview-only behavior, byte/deadline bounds, typed response checks,
truncation, redirect limits/downgrades/private destinations, denied access without
fallback, real descriptor remux, playlist rejection, backend gates, receipt reuse,
changed evidence, malformed receipts, empty transcripts and actual note citations.
The decoder boundary uses the [documented fd protocol](https://ffmpeg.org/ffmpeg-protocols.html#fd),
explicit protocol/demuxer restrictions and an owned worker deadline. It is not an
OS sandbox or a claim that all malformed-codec vulnerabilities are prevented.

Remaining acceptance: representative real podcast/paywall sources, independent
skill/harness evaluation, and the broader release checklist. Do not close #57
based only on these fixtures or passing structural tests.
