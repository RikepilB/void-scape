# Transcription backends

Read this when a backend errors (missing key / not installed) or when the user asks which to use.
The `run` cascade tries free sources first, then the backend you pass. Pass `--backend <name>` to force one.

| backend | `--backend` | $/min | cost | data leaves machine? | setup |
|---|---|---|---|---|---|
| Sidecar file | (auto) | 0 | free | no | a `.srt`/`.vtt`/`.txt` next to the video |
| URL captions | `captions` | 0 | free | no (yt-dlp pulls public subs) | none (yt-dlp installed) |
| faster-whisper | `faster-whisper` | 0 | free (CPU time) | **no** | `pip install faster-whisper` |
| trx | `trx` | 0 | free (CPU time) | **no** | `bun add -g @crafter/trx && trx init` |
| Groq | `groq` | ~0.0007 | cheapest API | yes → Groq | `GROQ_API_KEY` |
| OpenAI mini | `openai-mini` | 0.003 | cheap API | yes → OpenAI | `OPENAI_API_KEY` |
| OpenAI | `openai` | 0.006 | API | yes → OpenAI | `OPENAI_API_KEY` |
| OpenRouter | `openrouter` | ~0.006 | API (passthrough) | yes → OpenRouter | `OPENROUTER_API_KEY` |
| Gemini | `gemini` | ~0.037 | API (also analyzes) | yes → Google | `GEMINI_API_KEY` + `pip install google-genai` |

Rates are seeded in `pricing.json` (June 2026). Update them there if a provider's price changes.

## Decision order
1. **Sidecar transcript present?** Free and accurate — always wins. No flag needed.
2. **URL with captions?** `--backend captions`. Free, no upload, covers most public YouTube/Vimeo.
3. **Local file, privacy matters, no rush?** A local engine (`faster-whisper` or `trx`). Free, fully offline. One-time install + model download.
4. **Need a transcript now and willing to pay?** Cheapest API first: `groq` ≪ `openai-mini` < `openai`/`openrouter` < `gemini`.

## Free, offline (no key)
- **`faster-whisper`** — preferred local engine here: pure-Python wheel (CTranslate2, no PyTorch), lighter than trx. `pip install faster-whisper`. The skill calls it on CPU with `compute_type=int8`.
  - **Model size** defaults to **`small`** (≈ 484 MB) — the accuracy/size sweet spot for non-English speech (e.g. Spanish meetings); `tiny`/`base` are noticeably worse there, `medium`/`large-v3` better but slower. Override per machine via `whisper_model` in `workspace.json`, env `READ_VIDEO_WHISPER_MODEL` (a size name *or* a full path to a pre-downloaded model dir), or env `READ_VIDEO_WHISPER_DIR` (download_root / cache dir).
  - **Thorough mode:** `auto` uses the existing fast profile through 45s, then `--transcribe-mode thorough` behavior above that threshold: it requests `medium` when the machine is otherwise using the default `small`, sets `condition_on_previous_text=False`, and tightens VAD to `min_silence_duration_ms=500` / `speech_pad_ms=300`. `estimate` reports whether `medium` is cached; pass `run --allow-model-download` only after explicit consent. Override with `--transcribe-mode fast|thorough`, `workspace.json`'s `transcription_thorough_threshold_s`, or `READ_VIDEO_TRANSCRIPTION_THOROUGH_THRESHOLD_S`.
  - **Offline-first + graceful fallback:** a cached model is loaded with `local_files_only=True`, skipping the HuggingFace revision HEAD that fails on locked-down networks (`WinError 10054`) even when every file is on disk. If the requested size isn't cached it tries one online download (with retry); if that fails it falls back to a smaller *cached* size and prints a loud `WARNING` to stderr (no silent accuracy drop). If nothing loads it errors with offline-install guidance.
  - **No network to HuggingFace?** Cache a model once on a connected machine: `python -c "from faster_whisper import WhisperModel as W; W('small')"`, then point `whisper_model` / `whisper_model_dir` at it. Throughput here is ~7× realtime on CPU (74 s clip → ~10 s).
- **`trx`** — `crafter-station/trx` (MIT), whisper.cpp under the hood, agent-first JSON. Needs `bun`: `bun add -g @crafter/trx` then `trx init` (installs deps + downloads a Whisper model, tiny 75 MB → large 3 GB, configurable in `~/.trx/config.json`).

Both are $0 marginal — you pay only CPU time. Use them whenever the audio shouldn't leave the machine.

## Paid APIs (audio is uploaded — gate first)
Sending audio to any of these means the user's content leaves the machine and is billed per minute.
Only ever use a paid backend **after** the cost gate is approved. Comma-separated backend chains are gated by the most expensive backend in the chain, not the first backend, because runtime may fall through after a failure.

Every chain containing Groq, OpenAI, OpenAI-mini, OpenRouter, or Gemini also requires explicit
privacy approval. `run` rejects it before media download, audio conversion, or upload unless
`--allow-cloud` is present. An API key is not consent.

The OpenAI-compatible backends (Groq / OpenAI / OpenAI-mini / OpenRouter) need **no SDK** — `video.py`
uploads via pure-stdlib `urllib` (hand-built multipart), with a non-default User-Agent (Groq's Cloudflare
WAF 403s the default urllib UA) and exponential-backoff retry on 429 / transient network errors. Audio is
extracted to mono 64 kbps mp3 (~0.5 MB/min), so ~50 min fits the ~25 MB upload cap.

- **Groq** (`GROQ_API_KEY`) — `whisper-large-v3`. Cheapest and fastest API path; default paid fallback.
- **OpenAI** (`OPENAI_API_KEY`) — `--backend openai-mini` (`gpt-4o-mini-transcribe`, $0.003, plain text — no per-segment timestamps) or `--backend openai` (`whisper-1`, $0.006, timestamped).
- **OpenRouter** (`OPENROUTER_API_KEY`) — proxies `openai/whisper-1`; use when the user already has OpenRouter credits.
- **Gemini** (`GEMINI_API_KEY` or `GOOGLE_API_KEY`, `pip install google-genai`) — `gemini-2.5-flash`. The one paid backend that still needs an SDK. Priciest per minute, but transcribes *and* reasons over audio in one call; worth it when the task needs audio understanding beyond a plain transcript.

Set keys as environment variables (PowerShell: `$env:GROQ_API_KEY="..."`). The skill reads keys **only**
from the environment — it never scans `.env` files or writes keys to disk (a deliberate divergence from
upstream `codex-video`, which auto-loads `~/.config/watch/.env`).

## URL fetch: yt-dlp vs cobalt
- **yt-dlp** (installed) is the default for both metadata and captions — `--list-subs`/`--write-subs` get public captions without downloading the video, and it fetches media when frames are needed.
- **cobalt** (`imputnet/cobalt`, media-downloader proxy) is an optional fallback when yt-dlp is blocked. It has an HTTP API (`POST` to a cobalt instance) and is self-hostable via Docker, or use a public instance. Not wired into `video.py` by default — add it only if yt-dlp fails for a given source. See https://github.com/imputnet/cobalt/blob/main/docs/api.md.
