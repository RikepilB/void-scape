# Public YouTube ingestion

Repository-only workflow for selected public videos, playlists and channel tabs.
The [project skill](../.agents/skills/youtube-ingest/SKILL.md) connects bounded
discovery, durable capture, governed reading and verified notes. This is separate
from the OAuth-backed private-playlist queue adapter; no account mutation occurs.

## What works

- Canonical video identity across supported URL forms and playlists.
- Metadata-only preview and explicit capture of at most100 selected entries.
- Immutable selection snapshots, partial-write recovery and pending-note lookup.
- Ordered inspect/preview/read with local transcription gates and a process deadline.
- Verified notes with actual transcript/frame timestamps and retained provenance.

Use the [command reference](../.agents/skills/youtube-ingest/references/commands.md)
for executable examples and the exact note schema. Capture and read permissions
are distinct. No helper grants cloud processing, first model downloads, browser
credentials, external copying or account actions.

## Scope and recovery

A channel root selects its videos tab. Explicit `/shorts` and `/streams` tabs are
preserved. Ambiguous video-plus-playlist/time URLs and unsupported functional
queries are rejected rather than silently expanded or stripped. Enumeration
starts at1..10000 and returns at most100 items; a positional window is not proof
of complete channel history. yt-dlp flat metadata may omit author/date/access fields.

The selection snapshot is written and verified before per-video capture records.
Resume uses those selected IDs even if the remote playlist changes. Capture dedup
does not imply analysis: use retained lookup against the selected note root.
Changed metadata is reported while the original capture stays immutable. A
conflicting partial capture must be recovered from its original snapshot.

The read worker checks the validated YouTube ID in probe output because display
URLs redact query strings. It clears the legacy cookie environment binding and
uses the reader's explicit options. Media yt-dlp invocations ignore user config,
plugins, remote components, filesystem cache and playlist expansion. The packaged
dependency minimum is now yt-dlp2026.8.19, the verified version supporting these
controls. No dependency was installed or updated during this implementation.

Ready receipts bind the requested video, read options and artifact hashes.
Changed evidence blocks reuse and publication. A completed matching read can be
reused; an interrupted read needs inspection and a fresh work directory. Only
available local transcription is supported by this bounded worker. Caption failure
does not authorize an automatic cloud fallback or an uncached model download.

## Verification and limits

A real public playlist linked from blender.org returned exactly two video IDs in
a two-item window. A separate131-second video completed both visual and cached
local Whisper extraction. Its QA note was published with verified artifacts and
then disappeared from pending lookup. The note explicitly limits its visual claims
to seven inspected frame samples; a one-word transcript was not treated as a
reliable spoken summary. This demonstrates the local workflow, not speech accuracy
on every video or independent agent/harness performance.

The publisher validates provenance, hashes and timestamp existence. It cannot
prove that a semantic claim is true; the note author must inspect the actual
evidence and describe incomplete coverage. Skips remain separate from analysis.
Independent skill benchmarks, representative harness runs and broader source
acceptance remain pending under issue57. This workflow is not a globally installed
command or a scheduler.
