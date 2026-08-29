# Video and audio

The video reader prepares scoped frames and/or timestamped transcript evidence from local media and
supported public media URLs.

**Status:** `shipped`
[Back to agent docs](../index.md) · Entry points:
[`voidscape.py`](../../../skill/scripts/voidscape.py), [`video.py`](../../../skill/scripts/video.py)

## Choose evidence

| Tier | Use when | Evidence |
| --- | --- | --- |
| `visual` | Slides, UI, charts, demonstrations | sampled frames + manifest |
| `audio` | Speech is primary and visuals are static | transcript + manifest |
| `both` | Meaning depends on speech and visuals | frames + transcript + manifest |

`inspect` reports duration, dimensions, audio, caption/sidecar availability, and a recommended tier.
`preview` estimates transcription and agent evidence-reading cost before extraction.

## Backends and gates

- Existing sidecar `.srt`, `.vtt`, or `.txt`: local and reusable.
- Captions backend: uses available platform captions without speech transcription.
- Local faster-whisper: may require an approved first model download.
- Cloud transcription: audio may leave the machine only after current `--allow-cloud` approval.

Backend chains may fall back, but never across an unapproved cloud or model-download boundary.

## Guided use

```powershell
python skill/scripts/voidscape.py inspect "clip.mp4"
python skill/scripts/voidscape.py preview "clip.mp4" --tier both --backend captions
python skill/scripts/voidscape.py read "clip.mp4" --tier both --backend captions --workdir evidence
```

Use `--start`, `--end`, or explicit timestamps in the raw reader for focused evidence. Transcript
and frame timestamps remain on the absolute source timeline.

## Citation contract

Read `manifest.json`, `transcript.txt`, and `frames/` as available. Cite moments as `[MM:SS]` from
the source timeline. Do not claim content outside the extracted range or narrate motion from
near-identical frames.

Canonical details: [architecture](../../architecture.md), [CLI reference](../../cli-reference.md),
and [authenticated sources](../../authenticated-sources.md).
