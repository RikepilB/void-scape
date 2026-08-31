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

## Fast API path for long recordings

When turnaround matters more than keeping audio fully local, Voidscape can use `groq`,
`openai-mini`, `openai`, `openrouter`, or `gemini`. The cloud path still requires a current
`--allow-cloud` approval for the exact source and scope; an API key is configuration, not consent.

[Groq publishes a 189x real-time speed factor](https://console.groq.com/docs/speech-to-text) for
the `whisper-large-v3` model used by Voidscape. At that provider-published factor, six hours of
audio corresponds to about 114 seconds of model processing. This explains why the transcription
stage of a long recording can sometimes finish in under two minutes.

That number is not a Voidscape end-to-end SLA or a benchmark from this repository. Media download,
audio extraction, encoding, upload, provider queue and rate limits, network conditions, frame
extraction, and the agent's later evidence reading all add time. Run `preview` first and describe
the result as a provider-backed fast path—not a guaranteed completion time.

```powershell
$env:GROQ_API_KEY="..."
voidscape preview "long-recording.mp4" --tier audio --backend groq
voidscape read "long-recording.mp4" --tier audio --backend groq --allow-cloud --workdir evidence-long
```

Voidscape compresses API audio and automatically splits a single oversized recording under the
provider upload cap while preserving source-time offsets. Those chunks are submitted sequentially;
automatic chunking is not the same as a provider batch job.

## Multiple sources and provider batches

Voidscape processes one source per invocation. A calling agent may coordinate several independent
reads, but each source needs its own `inspect`, `preview`, approval decision, and unique work folder.
The repository does not ship a multi-video batch command, scheduler, or unattended approval loop.

[Groq's Batch API](https://console.groq.com/docs/batch) supports audio transcription at scale, but
Voidscape does not invoke that API today. Groq documents a 24-hour to 7-day processing window, so
that provider feature is useful for asynchronous throughput and cost—not for an under-two-minute
latency promise. Treat it as vendor-documented integration work until Voidscape implements and
tests a consent-preserving adapter.

## Guided use

```powershell
voidscape inspect "clip.mp4"
voidscape preview "clip.mp4" --tier both --backend captions
voidscape read "clip.mp4" --tier both --backend captions --workdir evidence
```

Use `--start`, `--end`, or explicit timestamps in the raw reader for focused evidence. Transcript
and frame timestamps remain on the absolute source timeline.

## Citation contract

Read `manifest.json`, `transcript.txt`, and `frames/` as available. Cite moments as `[MM:SS]` from
the source timeline. Do not claim content outside the extracted range or narrate motion from
near-identical frames.

Canonical details: [architecture](../../architecture.md), [CLI reference](../../cli-reference.md),
and [authenticated sources](../../authenticated-sources.md).
