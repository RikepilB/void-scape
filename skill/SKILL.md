---
name: voidscape
description: >-
  Inspect, preview, and read local videos, recordings, voice material, or supported video URLs.
  Use when a user asks to watch, summarize, transcribe, describe, extract timestamps, or answer a
  question about media. Voidscape prepares frames and a transcript, shows cost and privacy gates
  before any paid or remote action, and grounds answers in [MM:SS] evidence.
---

# Voidscape

Codex cannot directly inspect a video container. Voidscape turns it into frames, transcript text, and a
manifest, then makes the cost and privacy decision visible before work happens.

Use the guided flow for people:

```text
python scripts/voidscape.py inspect <input>
python scripts/voidscape.py preview <input>
python scripts/voidscape.py read <input> [approval flags]
```

`<input>` is a local path, an http(s) URL, or a bare filename when an installed
`workspace.json` has an `inbox_dir`.

## Required behavior

1. **Inspect first.** Determine duration, audio, captions/sidecar availability, and whether the
   question needs `visual`, `audio`, or `both`.
2. **Preview before reading.** Call `preview` or raw `estimate` for the chosen tier/backend. Show
   the human-readable preflight when approval is needed.
3. **Never infer consent.** If `requires_cloud_approval`, get a current explicit yes before adding
   `--allow-cloud`. If `needs_model_download`, get a separate explicit yes before adding
   `--allow-model-download`. An API key, a prior run, or the backend name is not consent.
4. **Read only approved evidence.** After `read`, inspect `manifest.json`, `transcript.txt`, and
   frames in filename order. Answer direct questions with `[MM:SS]` citations; otherwise produce a
   short TL;DR and chronological timestamped beats.
5. **Save Markdown only as an agent-authored result.** When workspace `out_dir` is configured, save
   the final answer there. The CLI creates evidence artifacts; it does not claim to write a semantic
   note itself.

## Scope selection

- `visual`: UI walkthroughs, slides, charts, scenes, or silent screen recordings.
- `audio`: voice memos, calls, podcasts, and spoken recordings where visual detail is irrelevant.
- `both`: general summaries and mixed visual/audio material.

Prefer the smallest scope that answers the question. A sidecar transcript or URL captions keep the
audio path free and local.

## Advanced, automation-safe interface

The stable `video.py` interface remains the right choice for scripts and subagents:

```text
python scripts/video.py manifest --compact
python scripts/video.py probe <input> --envelope --compact
python scripts/video.py estimate <input> --tier both --backend captions --envelope --compact
python scripts/video.py run <input> --tier both --backend captions --envelope --compact
```

The envelope is `{ok,data,error,meta}`. On failure, inspect `error.code`, `error.exit_code`, and
`error.retryable`; do not parse prose to decide whether to retry. Existing callers may omit the
envelope and retain the original JSON shape.

## Workflows and boundaries

- Local recordings and supported public video URLs are available now.
- The repository's Instagram capture workflow is source-specific and user-observed. It must append
  and verify a URL before unsaving a Reel; do not replace it with a generic browser action.
- Voice-note Markdown workflows are agent orchestration, not a new `video.py` capability.
- Substack/RSS intake, universal capture, and a hosted/scheduled product are planned. Never route
  text articles through the media engine or describe them as installed functionality.

Use `python scripts/voidscape.py doctor` to diagnose local readiness and
`python scripts/voidscape.py customize` to review local folders/defaults. Neither command reads or
writes API keys.
