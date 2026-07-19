# Security

## Reporting a vulnerability

Open a [GitHub issue](https://github.com/RikepilB/read-video/issues) or, for anything sensitive,
email the address on the maintainer's GitHub profile. There's no bug bounty — this is a single-
maintainer open-source project — but reports are read and acted on.

## Static scanner finding: env key → cloud transcription request

Running [SkillSpector](https://github.com/skillspector/skillspector) (`skillspector scan skill
--no-llm`) against this skill returns a `CRITICAL` / "do not install" verdict. Its taint analysis
flags one real data flow: an API key read from an environment variable
(`GROQ_API_KEY`/`OPENAI_API_KEY`/`OPENROUTER_API_KEY`/`GEMINI_API_KEY`) reaching an authenticated
HTTP request to a cloud transcription endpoint (`skill/scripts/video.py`, `BACKEND_API` /
`_api_transcribe` / `_gemini`). It separately flags the presence of external endpoints, `subprocess`
use, and undeclared permissions — all true, all necessary for a tool whose job is calling
`ffmpeg`/`yt-dlp`/local Whisper and, optionally, a paid transcription API.

**This is by design, not an oversight, and it's already gated:**

- **Local-first by default.** `estimate`'s default backend is `captions` (free, no key). Cloud
  backends are only ever used if the caller explicitly names one.
- **Consent before spend or upload.** `run` refuses to send audio to any cloud backend
  (`groq`/`openai`/`openai-mini`/`openrouter`/`gemini`) unless `--allow-cloud` is passed — checked
  *before* the file is even downloaded or converted to audio (see `tests/test_privacy_gate.py`).
  Having a key set in the environment is never treated as consent.
- **Keys never touch disk via this tool.** They're read only from environment variables
  (`os.environ`) — never from `.env`, never logged, never written into any output file this skill
  produces.
- **No SDK, no telemetry.** The cloud calls are hand-built `urllib` requests to the documented
  provider endpoint and nothing else; there's no analytics/telemetry dependency in this codebase
  to exfiltrate through.

If you want zero cloud capability, don't set any of the four API-key environment variables and
don't pass `--allow-cloud` — the tool then only ever exercises `captions`/`sidecar`/local
`faster-whisper`/`trx`, none of which make a network request with your audio.

## Scope

This scanner result covers the `skill/` bundle only. `scripts/instagram_capture_helper.py` and its
subagent (a separate, removable add-on — see `docs/architecture.md`) read no
credentials themselves; Instagram cookies are supplied by the user via an environment variable
they set, never scanned from a file by this project.
