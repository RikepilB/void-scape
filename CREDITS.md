# Credits & prior art

`read-video` stands on a lot of open-source shoulders. This file records what it borrows and why.

## Prior art / inspiration

- **[bradautomates/claude-video](https://github.com/bradautomates/claude-video)** — the upstream Claude
  skill that inspired this one. Several robustness ideas were grafted from it: extracting **mp3 (not wav)**
  so long audio fits provider upload caps, a **pure-stdlib multipart upload** path (no SDK), the Groq
  Cloudflare-WAF User-Agent workaround, and rolling-caption de-duplication for auto-generated subtitles.
  `read-video` diverges deliberately on two points: a **cost pre-flight gate** (price the whole job before
  any spend) and **env-var-only key handling** (it never scans or auto-loads `.env` files).
- v0.2.0 (2026-06): perceptual frame dedup (16x16 grayscale single-pass thumbnails),
  Whisper API auto-chunking with per-chunk gap tolerance, and `--timestamps` pinned
  frames were ported and adapted to this skill's fast-seek extraction and backend chain.

## Runtime dependencies

| Tool | Role | License |
|------|------|---------|
| **[ffmpeg / ffprobe](https://ffmpeg.org/)** | Probe media; extract frames + audio | LGPL/GPL |
| **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** | Download video URLs + fetch captions | Unlicense |
| **[faster-whisper](https://github.com/SYSTRAN/faster-whisper)** | Local CPU transcription (CTranslate2, no PyTorch) | MIT |
| **[trx](https://github.com/crafter-station/trx)** | Alternative local engine (whisper.cpp, agent-first JSON) | MIT |
| **Whisper models** ([Systran on Hugging Face](https://huggingface.co/Systran)) | `tiny`/`base`/`small`/`medium`/`large-v3` weights | MIT |

Optional paid backends (all OpenAI-compatible `/audio/transcriptions`): **Groq**, **OpenAI**, **OpenRouter**,
**Google Gemini**. Keys are read only from environment variables.
