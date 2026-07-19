# Architecture

This document explains *how* `read-video` works and *why* it's shaped the way it is. If you just want to
use it, the [README](../README.md) is enough; read this if you want to extend it or understand the cost model.

## The core problem

Codex's `Read` tool renders **images and PDFs**, but it cannot ingest a video container. So there is no
"read this `.mp4`" primitive. To let an agent reason about a video you must first decompose it into modalities
the model *can* read:

- **Visual channel** → extract still **frames** (JPGs). Codex sees these as images.
- **Audio channel** → produce a **transcript** (text), ideally with `[MM:SS]` timestamps.

Everything in this project follows from that one fact, plus a second one: **the frames are the expensive
part.** A frame is a vision-heavy input; a dozen minutes of video at a naive frame rate is hundreds of them.
The bottleneck is rarely transcription dollars — it's Codex's own token consumption reading frames. That's
why the architecture is built around *pricing the job before doing it.*

## Two channels, independently selectable

`--tier` picks which channels you pay for:

| tier | frames | transcript | when |
|---|---|---|---|
| `visual` | ✅ | — | screen has the content (slides, UI, charts) and there's no/irrelevant audio |
| `audio` | — | ✅ | a meeting/talk where the screen is near-static — the substance is spoken |
| `both` | ✅ | ✅ | general case |

A screen-recorded meeting is the classic case where `audio` alone is the right call: the visual is a frozen
shared screen, so paying for 100 frames is waste — the value is entirely in what people *said*.

## The cost model

`estimate` computes two **separate** costs, because they are not the same kind of money:

1. **Transcription `$` — out-of-pocket.** Real dollars billed by a cloud API. Local/caption paths are `$0`.
   ```
   transcription_usd = duration_min × rate[backend]      # rate from pricing.json
   ```
2. **Agent `$` — token cost.** What Codex spends reading the frames + transcript and writing the answer.
   ```
   read_tokens = frames_tokens + transcript_tokens + 2000(overhead)
   agent_usd   = read_tokens/1e6 × model_input_rate + output_tokens/1e6 × model_output_rate
   ```

The gate reports both, the **total**, and the **dominant driver** (`frames` / `transcript` / `output`). The
`free` flag keys on `transcription_usd == 0` — i.e. "no out-of-pocket spend" — *not* on total tokens, because
a free-to-transcribe job can still be a large token job worth flagging.

### Frame budget (keeps the dominant cost bounded)

Frames are chosen adaptively by duration, then hard-capped so you never blow past 2 fps or 100 frames:

```python
duration ≤ 30s   → 30 frames
duration ≤ 3min  → 60
duration ≤ 10min → 80
else             → 100
hard cap = min(budget, 100, duration × 2)
```

### Per-frame token math

Codex's vision cost is roughly `(width × height) / 750` tokens. Frames are downscaled to **512 px wide**
(`scale=512:-2` in ffmpeg, preserving aspect, even height) *before* Codex reads them — which is the single
biggest lever on cost:

```python
height          = round(512 × src_h / src_w)        # assume 16:9 if resolution unknown
per_frame_tokens = ceil(512 × height / 750)
frames_tokens    = n_frames × per_frame_tokens
```

Transcript tokens are estimated at `duration_min × 200` (~150 wpm × ~1.33 tokens/word).

All rates live in **`pricing.json`** (`transcription_per_min`, `model_per_mtok._active`, `frame.target_width`)
so they can be re-tuned without touching code.

## The backend cascade

Transcription backends are tried cheapest-and-most-private first. The skill prompt encodes this preference;
the engine implements each path:

```
sidecar .srt/.vtt   (free, already on disk)
   └─► URL captions  (free, yt-dlp)
        └─► faster-whisper / trx   (free, local CPU, audio never leaves the machine)
             └─► Groq               (~$0.0007/min, cheapest API)
                  └─► OpenAI-mini / OpenAI / OpenRouter
                       └─► Gemini   (~$0.037/min)
```

The paid backends are all **OpenAI-compatible** `/audio/transcriptions` endpoints, hit with a hand-built
multipart body over pure-stdlib `urllib` — **no SDK install**. Two robustness details matter:

- **mp3, not wav.** For the **API** path, audio is extracted as mono 16 kHz **64 kbps mp3** (~0.5 MB/min), so
  ~50 minutes fits the providers' ~25 MB upload cap. (wav at ~1.9 MB/min blows the cap after ~13 min.) Local
  backends skip this encode and read the media directly (see Performance below).
- **Groq's WAF.** Groq sits behind Cloudflare, which 403s the default `urllib` User-Agent — so requests send
  a custom UA. 429s and network resets get exponential-backoff retry.

### Offline-resilient local transcription

`faster-whisper` is the recommended local engine. Two failure modes are handled explicitly, because they bit
this project in testing:

1. **Cached-but-blocked.** Even when a model is fully cached, `WhisperModel` does an online HEAD to validate
   the revision — which fails on locked-down networks (`WinError 10054`). Fix: load cached models with
   `local_files_only=True`, skipping the network round-trip entirely.
2. **Missing model.** If the requested size isn't cached, the engine tries one online download (with retry).
   If that fails it falls back to a smaller **cached** size and prints a loud `WARNING` to stderr — never a
   *silent* accuracy drop. If nothing loads, it errors with offline-install guidance.

Model size is configurable (`whisper_model` in `workspace.json`, or `READ_VIDEO_WHISPER_MODEL` /
`READ_VIDEO_WHISPER_DIR` env). Default is **`small`** — the accuracy/size sweet spot for non-English speech.

## Performance

The naïve implementations of both channels scale with *video length*; the engine makes them scale with the
*work actually requested* instead.

- **Frame extraction scales with frame count, not duration.** A single `fps=N/duration` filter pass forces
  ffmpeg to decode the entire stream and discard all but N frames — on a 9-min 60 fps source that's ~33k
  decoded frames to keep 80. Instead, each sampled frame is grabbed with an independent **fast input seek**
  (`-ss` *before* `-i`, one frame out, scaled in the same pass), and the seeks run in a small thread pool.
  Cost becomes O(frames), not O(duration × fps): the same 9-min clip extracts in ~5 s instead of minutes.
  Seeking is keyframe-accurate rather than exact, which is the right trade for *sampling the gist* of each
  moment. A whole-stream filter pass remains as a fallback for containers that don't seek cleanly.
- **Local transcription reads the media directly.** `faster-whisper` decodes audio itself (PyAV/ffmpeg), so
  the engine hands it the source file — no separate lossy mp3 pass (that exists only to satisfy the API
  upload cap), which also avoids the quality loss of a 64 kbps re-encode.
- **VAD skips silence.** Local transcription runs with Silero **VAD** (`vad_filter=True`, no extra
  dependency). On sparse or silent audio — e.g. a screen recording with only background music — Whisper
  processes the speech segments instead of the whole timeline, turning minutes of work into seconds. It also
  suppresses Whisper's tendency to *hallucinate* text over silence, so a near-silent clip returns an
  honestly-empty transcript instead of plausible-looking noise.

Net effect on a 9-min 1080p60 screen recording: a `both`-tier run dropped from ~12 min to well under a
minute, with the frame pass alone going from the dominant cost to ~5 s.

## Security posture

- **Keys come only from environment variables.** The engine never scans, reads, or auto-loads `.env` files.
  (This is a deliberate divergence from the upstream `codex-video`, which auto-loads a dotenv.)
- **Audio is local by default.** A cloud backend means audio leaves the machine — the skill only does that
  after the user approves it at the gate.
- **No personal config in the repo.** `workspace.json` (which holds absolute machine paths) is gitignored;
  the repo ships `workspace.example.json`.

## Data flow

```
probe(input)
  ├─ local file ─► ffprobe         → {duration, w, h, fps, has_audio, sidecar?}
  └─ URL        ─► yt-dlp -J        → {duration, w, h, fps, captions_available, title}

estimate(input, tier, backend)
  └─ probe + frame budget + token math + pricing.json   → cost breakdown JSON (the GATE)

run(input, tier, backend, [start,end,frames,workdir])
  ├─ acquire media (download URL, or use the local path) — only if pixels/non-caption audio are needed
  ├─ frames:    ffmpeg fps=n/window, scale=512:-2        → workdir/frames/*.jpg (+ [MM:SS] in manifest)
  ├─ transcript: backend cascade → mp3 → engine/API      → workdir/transcript.txt
  └─ manifest.json mapping every frame to its timestamp

→ Codex `Read`s the frames + transcript and writes the grounded answer.
```

See [cli-reference.md](cli-reference.md) for exact arguments and JSON shapes, and
[workflow.md](workflow.md) for how the agent is told to drive all this.
