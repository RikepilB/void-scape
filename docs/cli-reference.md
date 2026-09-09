# CLI / API reference — `scripts/video.py`

Reader polish: image manifests use `source: "local"` and `input` for the source
path, matching image probe/estimate and the article reader. Consumers that used
the former image `source` path must read `input` instead. Guided URL commands trim
surrounding whitespace consistently before routing and dispatch.

The pricing snapshot was reviewed on 2026-09-08 against
[OpenAI standard short-context pricing](https://developers.openai.com/api/docs/pricing)
and [Groq speech pricing](https://console.groq.com/docs/speech-to-text).
Groq selects `whisper-large-v3`, so its estimate uses $0.111/hour rather than the
turbo model's rate. Minimum request billing, retries, long context, caching, and
service tiers can change actual charges. Gemini and OpenRouter minute rates remain
explicitly labeled legacy estimates. The bundled snapshot and fallback rates agree.

For the guided human path, start with [Voidscape's guide](voidscape-guide.md):
`voidscape.py inspect → preview → read`. This page documents the stable lower-level engine used by
existing scripts, subagents, and non-interactive automation.

The guided CLI also exposes two zero-mutation discovery commands:

```powershell
voidscape sources --json
voidscape route <file-or-url> --json
```

`sources` returns the truthful platform/reader/capture matrix. `route` selects the default reader
and lists safe alternatives. Mixed sources can use `--reader video|article|image` on `inspect`,
`preview`, and `read`; the override never grants fetch, cloud, model, browser, or account approval.
Route/probe metadata strips URL credentials, query values, and fragments before printing or writing
evidence; the selected input is still used internally only for its approved operation.
See [source capabilities](source-capabilities.md).

The engine is a single Python CLI with four subcommands. It is **agent-first**: every command prints
**JSON** to stdout, unless you pass `--human` for a readable estimate. Existing callers retain the
legacy JSON shape; agents can opt into a stable envelope and deterministic exit metadata.

On Windows, the guided CLI and raw video, image, article, and chat entrypoints
configure stdout and stderr as UTF-8, including redirected output. Decode captured
output as UTF-8. Embedded streams without reconfiguration support are left intact.

Successful reads also write `<workdir>/.agent/latest-read.json`, containing relative
evidence paths, a manifest SHA-256, completion time, and schema version. Paths resolve
against the workdir, not the `.agent` folder. Use an explicit `--workdir` for recovery
when terminal output is truncated. Run once in the foreground; waiting on that
process handle is supported. After successful exit, read the pointer once and then
the manifest and required evidence. Do not poll directories or rerun the read just
to recover output. A pointer is navigation metadata, not proof that source content
is trustworthy. Failed runs may leave partial files; never reuse their pointer as
proof of success. Existing nonempty workdirs remain rejected.

```
python scripts/video.py manifest [--compact]
python scripts/video.py <probe|estimate|run> <input> [flags]
```

For command discovery, run `python scripts/video.py manifest --compact`. Every operational command
accepts `--envelope` for `{ok,data,error,meta}` and `--compact` for single-line token-efficient
JSON. Exit codes are `0` success, `1` unexpected error, `2` usage error, `3` input error, `4`
approval required, `5` dependency error, and `6` operation failure. Envelope errors repeat the
numeric value in `error.exit_code` and include `error.code` plus `error.retryable`.

Read results record `status`, `stages_completed`, and `warnings`. A clean completed
read has `status: complete` and an empty warnings list. Completed reads may still
have coverage warnings, such as a failed audio chunk; read those warnings before
claiming a complete transcript. Envelopes expose the same list as `meta.warnings`.

When a later stage fails after usable artifacts were written, the command keeps
its original nonzero exit and `ok: false`. Its `data` contains only the completed
artifact records, with `status: partial`; `meta.failed_stage` names the failed
operation and `meta.stages_completed` lists successful stages. The partial
`manifest.json` records the same state. `meta.manifest_written` explicitly says
whether persistence succeeded. A failure to save diagnostics does not replace the
original error. Never treat files omitted from that record as completed evidence.

Partial reads never receive a success `.agent/latest-read.json` pointer. If the
recovery-pointer step fails after the complete manifest was saved, the manifest
remains complete and the error identifies `failed_stage: recovery`; this is a
recovery failure, not a failed transcription. Permission refusals remain hard
failures without partial-result warnings. Existing exit codes are unchanged.

Stages are reader-specific: `probe`, `validate`, `workdir`; video `acquire`, `scope`,
`frames`, `transcribe`; image `copy`; article `fetch`, `write_entries`; chat
`write_transcript`; and finally `manifest`, `recovery`. Skipped stages are not
listed as completed. A failed multi-item copy/write may retain individual
completed artifacts even though the overall stage did not complete.

Gate failures also include `error.gate`: `type` is `cloud_approval`, `model_download`,
or `missing_credentials`, and `backend` identifies the selected backend or chain.
Missing credentials include an `env_var` **name**, never its value. For Gemini,
`GOOGLE_API_KEY` is also accepted when the primary `GEMINI_API_KEY` is unset.
Failed backend chains or fully failed chunked requests preserve individual gates
in `error.gates`; other failures may coexist, so this list is not the sole diagnosis.

Video/article preview includes `gate` for the first approval requirement, or `null`.
The existing `requires_cloud_approval` and `needs_model_download` flags remain
authoritative when both approvals are needed. Preview never checks API keys.
Credentials are checked only when an approved cloud backend is actually attempted;
free sidecars and successful earlier fallbacks do not require unused keys.

Exit compatibility is unchanged: preflight approval failures return 4; a direct
missing-key failure returns 5. Existing aggregate/runtime failures can still return
6 (for example, a model-cache failure discovered during execution). Inspect gate
metadata as well as the exit code. Resolve the requested action once, then rerun
only with the user's current approval. Set keys locally in the process environment;
never paste values into agent conversations or save them in workspace configuration.

Error output removes URL credentials/query strings, recognizable credential fields,
authorization headers, and common provider-token prefixes. This applies before
fallback logging and before synthetic transcript-gap markers are written. Successful
source transcripts and article/chat evidence are not rewritten by this sanitizer.
Raw HTTP rejection bodies and Gemini SDK error details are omitted; backend/status
and error classification remain available. Pattern matching cannot identify every
possible secret in arbitrary prose, so these raw provider bodies are not logged.

`<input>` is a local path, a video URL, or — when a workspace is configured — a **bare filename** that
resolves against `inbox_dir`.

Only `ffmpeg`/`ffprobe` (and `yt-dlp` for URLs) are required for the free paths. Transcription engines are
imported lazily, so a missing optional dependency never breaks `probe`/`estimate`.

## Local image and carousel engine

The sibling image engine uses the same protocol and exit-code contract:

```bash
python scripts/image.py manifest --compact
python scripts/image.py probe "slides" --envelope --compact
python scripts/image.py estimate "slides" --envelope --compact
python scripts/image.py run "slides" --workdir slide-evidence --envelope --compact
```

It accepts JPG/JPEG, PNG, and WebP. One folder is one local, non-recursive carousel in natural
filename order (`slide1`, `slide2`, `slide10`), capped at 100 images for `estimate` and `run`.
Every supported image must contain exactly one frame. Animated APNG and WebP inputs are unsupported
and fail validation before preview or evidence copying.
`run` copies original bytes into `images/`, writes `manifest.json` only after all copies succeed,
and rejects a non-empty workdir. Agents cite the ordered evidence as `[image 1]`, `[image 2]`, and
so on; image evidence has no fabricated video timestamp. No OCR, cloud call, resize, or source-file
modification occurs.

---

## `probe` — inspect the input

```bash
python scripts/video.py probe "clip.mp4"
python scripts/video.py probe "https://youtu.be/VIDEO_ID"
```

**Local output:**
```json
{
  "source": "local",
  "input": "clip.mp4",
  "sidecar_transcript": null,        // path to a .srt/.vtt/.txt next to the file, if any
  "captions_available": false,       // true if a sidecar exists
  "duration_s": 73.6,
  "width": 1920, "height": 1080,
  "fps": 30.0,
  "has_audio": true
}
```

**URL output** adds `"title"` and `"captions_available"` (true if the platform exposes subs/auto-captions),
and `source` is `"url"`.

---

## `estimate` — price the job (the cost gate)

```bash
python scripts/video.py estimate "clip.mp4" --tier both --backend faster-whisper --human
```

| flag | default | meaning |
|---|---|---|
| `--tier` | `both` | `visual` / `audio` / `both` — which channels to price |
| `--backend` | `captions` | transcription backend or comma-separated fallback chain to price (see [backends](../skill/references/backends.md)) |
| `--frames` | adaptive | override the frame count |
| `--out-words` | `600` | assumed length of Codex's written answer (drives output-token cost) |
| `--transcribe-mode` | `auto` | `auto` / `fast` / `thorough` faster-whisper profile; overrides duration routing |
| `--agent-model` | `pricing.json`'s `_active` | model rate and vision-token preset; includes GPT-5.6 Sol/Terra/Luna and Codex presets |
| `--human` | off | print a readable table instead of JSON |

**JSON output:**
```json
{
  "input": "clip.mp4", "source": "local", "duration_s": 73.6,
  "tier": "both", "backend": "faster-whisper", "frames": 60, "per_frame_tokens": 144,
  "tokens": { "frames": 8640, "transcript": 245, "output": 798, "overhead": 2000, "read_total": 10885 },
  "cost_usd": { "transcription": 0.0, "agent": 0.0392, "total": 0.0392 },
  "dominant_cost": "frames",
  "free": true,                       // no out-of-pocket $ (agent tokens may still apply)
  "needs_install": false,             // any chosen local backend needs install
  "transcribe_mode": "thorough",      // faster-whisper only; otherwise "none"
  "agent_model": "gpt-5.6-terra",
  "vision_estimator": "openai_patch32",
  "cost_basis": "API-equivalent estimate; Codex subscription usage may not be billed per API token",
  "requires_cloud_approval": false,
  "needs_model_download": true,
  "model_download": { "status": "required", "model": "medium" },
  "sidecar_transcript": null,
  "captions_available": false,
  "note": "frame dedup may reduce actual frames below this count"
}
```

`note` is only present when the tier prices frames (`visual`/`both`): the gate prices the full frame
budget as a worst case, and `run`'s dedup can only shrink the real count from there.

`--human` renders the same data as:
```
input: clip.mp4  (local, 73.6s)
tier=both  backend=faster-whisper  frames=60
agent=gpt-5.6-terra  vision=openai_patch32
  frames tokens:         8640
  transcript tokens:      245
  output tokens:          798
  ---
  transcription: $0.0000
  agent tokens:  $0.0392
  TOTAL:         $0.0392   (dominant: frames)
  basis: API-equivalent estimate; Codex subscription usage may not be billed per API token
  APPROVAL: one-time model download required (medium)
```

**This is the gate.** The agent waits if `free` is false, `needs_install` or
`needs_model_download` is true, or `requires_cloud_approval` is true. If `--backend` is a
comma-separated chain, `estimate` prices the most expensive backend in the chain, detects missing
local dependencies anywhere in it, and requires cloud approval if any fallback could upload audio.

---

## `run` — extract frames + transcript

```bash
python scripts/video.py run "clip.mp4" --tier both --backend faster-whisper
python scripts/video.py run "clip.mp4" --tier audio --backend groq --allow-cloud --start 60 --end 180
```

| flag | default | meaning |
|---|---|---|
| `--tier` | `both` | `visual` / `audio` / `both` |
| `--backend` | `captions` | transcription backend or comma-separated fallback chain |
| `--frames` | adaptive | override frame count |
| `--start` / `--end` | `0` / full | analyze only a time window (seconds) |
| `--workdir` | temp dir | where to write outputs (frames, transcript, manifest) |
| `--timestamps` | none | comma-separated pins (`SS`/`MM:SS`/`HH:MM:SS`, e.g. `90,05:30`) reserved against the frame budget and never dropped by dedup |
| `--no-dedup` | off | keep every sampled frame instead of dropping perceptual near-duplicates |
| `--transcribe-mode` | `auto` | `auto` / `fast` / `thorough` faster-whisper profile; overrides duration routing |
| `--allow-cloud` | off | explicit consent to use any cloud backend in the chain; rejected before conversion/upload otherwise |
| `--allow-model-download` | off | explicit consent for a one-time faster-whisper model download |
| `--human` | off | (run always emits JSON; flag is accepted for symmetry) |

**Output** (also written to `<workdir>/manifest.json`):
```json
{
  "workdir": "/tmp/readvideo_ab12",
  "tier": "both",
  "backend": "faster-whisper",
  "frames": [
    { "file": ".../frames/frame_0001.jpg", "t": "00:01" },
    { "file": ".../frames/frame_0002.jpg", "t": "00:03" }
  ],
  "frames_deduped": 4,
  "transcript": ".../transcript.txt",
  "transcript_chars": 254
}
```

Each frame carries the `[MM:SS]` timestamp of its window midpoint, so Codex can cite moments precisely. A
pinned frame (from `--timestamps`) additionally carries `"pinned": true`. By default extraction oversamples
~2x the frame budget and drops perceptual near-duplicates, so `frames` may come back smaller than the
budget — `frames_deduped` is the count of frames dropped that way. Pass `--no-dedup` to disable it. The
agent then `Read`s the listed JPGs and the transcript file and writes the answer.

Approval flags are capabilities for one invocation, not persistent configuration. Pass them only
after the user has reviewed the matching estimate and explicitly consented.

> `faster-whisper` prints which model it actually used to **stderr** (`[read-video] faster-whisper model: small`,
> or a `WARNING` if it fell back). Watch that line — it tells you whether you got full accuracy.

---

## Environment variables

| var | used by |
|---|---|
| `GROQ_API_KEY` / `OPENAI_API_KEY` / `OPENROUTER_API_KEY` / `GEMINI_API_KEY` (`GOOGLE_API_KEY` also accepted for Gemini) | the matching paid backend |
| `READ_VIDEO_WHISPER_MODEL` | override faster-whisper size (`tiny`/`base`/`small`/`medium`/`large-v3`) or a model-dir path |
| `READ_VIDEO_WHISPER_DIR` | faster-whisper `download_root` / cache dir |
| `READ_VIDEO_TRANSCRIPTION_THOROUGH_THRESHOLD_S` | seconds above which `auto` uses the thorough faster-whisper profile |
| `READ_VIDEO_YTDLP_COOKIES` | optional path to a user-exported Netscape `cookies.txt` for a site the user is permitted to access |

Keys are read **only** from the environment — never from `.env`.

Voidscape does not extract browser cookies. Keep cookie files outside the repository and follow the
[authenticated-source guide](authenticated-sources.md).

## Config files (in the skill dir)

- **`pricing.json`** — `transcription_per_min[backend]`, model rates and vision estimator, `frame.target_width`.
- **`workspace.json`** (gitignored; copy from `workspace.example.json`) — `inbox_dir`, `out_dir`, `whisper_model`.
