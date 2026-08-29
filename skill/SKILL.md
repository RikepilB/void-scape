---
name: voidscape
description: >-
  Inspect, preview, and read local images, filename-ordered carousels, videos, recordings, voice
  material, articles, RSS or Atom feeds, and supported public URLs.
  Use when a user asks to watch, summarize, transcribe, describe, extract timestamps, or answer a
  question from media or article evidence. Voidscape shows cost and privacy gates before any paid
  or remote action and grounds answers in [image 1], [MM:SS], [article N], or [entry N] evidence.
---

# Voidscape

Voidscape gives Codex ordered evidence it can inspect: local images, carousels, and decomposed
video/audio plus a manifest. It makes the cost and privacy decision visible before work happens.

Use the guided flow for people:

```text
python scripts/voidscape.py inspect <input>
python scripts/voidscape.py preview <input>
python scripts/voidscape.py read <input> [approval flags]
```

`<input>` is a local image, a non-recursive folder containing up to 100 images, a local media path,
a local HTML/Markdown article, an RSS/Atom source, an approved public URL, or a bare filename when an
installed `workspace.json` has an `inbox_dir`.

## Required behavior

1. **Inspect first.** For images, verify natural filename order and dimensions. For video/audio,
   determine duration, audio, captions/sidecar availability, and whether the question needs
   `visual`, `audio`, or `both`.
2. **Preview before reading.** Call `preview` or raw `estimate` for the chosen tier/backend. Show
   the human-readable preflight when approval is needed.
3. **Never infer consent.** If `requires_cloud_approval`, get a current explicit yes before adding
   `--allow-cloud`. If `needs_model_download`, get a separate explicit yes before adding
   `--allow-model-download`. An API key, a prior run, or the backend name is not consent.
4. **Read only approved evidence.** For a local image/carousel, inspect `manifest.json` and
   `images/` in filename order and cite `[image 1]`, `[image 2]`, and so on without inventing OCR or
   timestamps. For video/audio, inspect `manifest.json`, `transcript.txt`, and frames; answer direct
   questions with `[MM:SS]` citations.
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

Local images and carousels have the matching raw interface:

```text
python scripts/image.py manifest --compact
python scripts/image.py probe <image-or-folder> --envelope --compact
python scripts/image.py estimate <image-or-folder> --envelope --compact
python scripts/image.py run <image-or-folder> --workdir <empty-folder> --envelope --compact
```

Folder reads are local, non-recursive, naturally ordered, and capped at 100 images. Originals are
copied byte-for-byte into the evidence bundle and never modified.

Articles and feeds have the same raw protocol:

```text
python scripts/article.py manifest --compact
python scripts/article.py probe <article-or-feed> --envelope --compact
python scripts/article.py estimate <article-or-feed> --envelope --compact
python scripts/article.py run <article-or-feed> --workdir <empty-folder> --envelope --compact
```

The envelope is `{ok,data,error,meta}`. On failure, inspect `error.code`, `error.exit_code`, and
`error.retryable`; do not parse prose to decide whether to retry. Existing callers may omit the
envelope and retain the original JSON shape.

## Workflows and boundaries

- Local images, filename-ordered carousels, recordings, articles, RSS/Atom feeds, and supported
  public URLs are available now.
- The repository's Instagram capture workflow is source-specific and user-observed. It must append
  and verify a URL before unsaving a Reel; do not replace it with a generic browser action.
- Voice-note Markdown workflows are agent orchestration, not a new `video.py` capability.
- The installed observe companion can capture one explicit desktop screenshot or short silent clip
  on Windows or Linux X11. It is not a browser controller or ambient recorder.
- Universal browser capture and a hosted/scheduled product are planned. Never describe them as
  installed functionality.

## Observe companion

Use the sibling capture CLI only when the user has authorized capture of the current desktop state:

```text
python scripts/observe.py doctor
python scripts/observe.py screenshot --out <new-path.png>
python scripts/observe.py clip --seconds <1-300> --out <new-path.mp4>
python scripts/observe.py status --json
```

Capture is local, full-desktop/display, silent, and on demand. It refuses existing destinations and
never reads cookies, browser storage, or credentials. `status` may read normalized optional
screenpipe health over loopback HTTP; it never installs, starts, or queries screenpipe history. Pass
the captured path through a separate `inspect -> preview -> read` flow and obtain every cloud or
model-download approval normally.

Use `python scripts/voidscape.py doctor` to diagnose local readiness and
`python scripts/voidscape.py customize` to review local folders/defaults. Neither command reads or
writes API keys.
