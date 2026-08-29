# Contributing to read-video

Thanks for taking the time — this skill is meant to improve over time, and outside eyes catch things the
author can't. Issues and PRs are both welcome.

## Ground rules

- **Keep the cost gate sacred.** The whole point of the skill is that it never spends money or sends audio to
  a cloud API without showing a price and getting a yes. Any change that lets `run` bill a provider or upload
  audio *before* the gate is a regression, not a feature.
- **Privacy first.** Keys come only from environment variables — never add `.env` scanning/auto-loading. Never
  commit a `workspace.json`, a transcript, a media file, or a key (`.gitignore` already blocks these — don't
  weaken it).
- **Smallest change that solves it.** Match the surrounding style in `video.py` (type hints, lazy imports for
  optional deps, JSON-out for the agent). No drive-by refactors in a feature PR.

## Project layout

| path | what |
|---|---|
| `skill/scripts/voidscape.py` | guided CLI — `inspect` / `preview` / `read` dispatch to the reader below |
| `skill/scripts/video.py` | video/audio engine + shared envelope/pricing/error helpers |
| `skill/scripts/image.py` | local image and carousel evidence engine |
| `skill/scripts/article.py` | local HTML/Markdown/RSS/Atom and non-video URL evidence engine |
| `skill/SKILL.md` | the prompt that tells Codex how to drive the engines |
| `skill/pricing.json` | editable rate table (transcription $/min, model $/Mtok, frame width) |
| `skill/references/backends.md` | per-backend setup |
| `docs/` | architecture / CLI reference / workflow / evals |
| `scripts/capture_adapter.py` | shared capture-adapter contract and urls.md queue helpers |
| `scripts/*_capture_helper.py` | platform-specific capture CLIs (Instagram, YouTube, …) |

Read [`docs/architecture.md`](docs/architecture.md) before changing the cost model or frame/token math.

### Adding or changing a media reader

Phase 0.2 (issue #15) decided on a **documented protocol, not a shared implementation layer**.
Each reader should expose `manifest`, `probe`, `estimate`, and `run` with the exit codes in
`video.py`'s manifest, reuse `video._envelope` / `video._classify_error` for agent output, and
register input discovery in `voidscape.py`. Keep probe/estimate/run payloads focused — do not force
video-only fields (`tier`, `backend`, frames) onto text or image readers. See
[`docs/superpowers/specs/2026-08-28-media-reader-interface-reassessment.md`](docs/superpowers/specs/2026-08-28-media-reader-interface-reassessment.md).

## Dev setup

```bash
# system: ffmpeg/ffprobe on PATH; yt-dlp for URL tests
pip install faster-whisper        # for local-transcription paths

# the engine is pure-stdlib otherwise — run it directly:
python skill/scripts/video.py probe   "samples/your-clip.mp4"
python skill/scripts/video.py estimate "samples/your-clip.mp4" --tier both --human
python skill/scripts/video.py run      "samples/your-clip.mp4" --tier audio --backend faster-whisper
```

There's no build step. `python -m py_compile skill/scripts/video.py` should stay clean.

## Testing a change

This skill is validated with Codex's **skill-creator** eval loop (with-skill vs no-skill baselines).
See [`docs/evals.md`](docs/evals.md). For a code change, at minimum:

1. `py_compile` is clean.
2. `probe` / `estimate` still emit valid JSON on a local file **and** a URL.
3. If you touched a backend, transcribe a short clip end-to-end with it.
4. If you touched the frame/token math, sanity-check `estimate --human` numbers against `docs/architecture.md`.

Note what you ran (and the output) in the PR — "tests pass" without evidence isn't enough.

## Capture adapters

Platform capture helpers share the **inspect → preview → process** contract and
urls.md dedup/append logic in [`scripts/capture_adapter.py`](scripts/capture_adapter.py).
Read [`docs/capture-adapters.md`](docs/capture-adapters.md) before adding a new platform.

**Extension sketch:** implement `canonical_url`, wire `preview_action_for_url` /
`append_and_confirm` for queue writes, keep OAuth or browser selectors inside your
helper, and add `tests/test_<platform>_capture_helper.py` plus contract coverage in
`tests/test_capture_adapter.py`. See the ExampleSocial walkthrough in the doc.

## Good first issues

- **Visual-change frame selection** — replace the fixed frame budget with keyframe/scene-change detection so
  near-static screen recordings don't over-sample.
- **More backends** — local whisper.cpp variants, Deepgram, AssemblyAI (keep them behind the gate).
- **Cross-platform paths** — the author develops on Windows; macOS/Linux path + ffmpeg testing is valuable.
- **Better non-English defaults** — language hints, model-size recommendations per language.

## PR checklist

- [ ] Cost gate still blocks spend/upload before a user yes
- [ ] No secrets / media / personal config added; `.gitignore` intact
- [ ] `py_compile` clean; `probe`/`estimate` JSON valid
- [ ] Docs updated if behavior/flags changed
- [ ] PR describes what you tested and the result

By contributing you agree your contributions are licensed under the repo's [MIT License](LICENSE).
