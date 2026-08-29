# Media-reader interface reassessment

**Date:** 2026-08-28  
**Status:** Decided — closes GitHub issue #15  
**Branch:** `chore/post-merge-verification`  
**Milestone:** ROADMAP Phase 0.2

## Goal

After shipping `article.py` (local HTML/Markdown and RSS/Atom) alongside `image.py` and `video.py`,
decide whether to extract a generic media-reader implementation or keep focused sibling engines
with a documented protocol only.

## Decision

**Adopt a small shared protocol. Do not extract a shared implementation layer.**

- **Protocol (documented contract):** each reader exposes `manifest`, `probe`, `estimate`, and
  `run` with the same exit-code map and optional `{ok,data,error,meta}` envelope. The guided CLI
  (`voidscape.py`) maps human commands `inspect → preview → read` onto `probe → estimate → run`.
- **Implementation:** keep three focused modules (`video.py`, `image.py`, `article.py`). Shared
  infrastructure stays in `video.py` (envelope, error classification, pricing helpers) as imports,
  not as a reader base class or generic pipeline.
- **Rationale:** three concrete shapes are enough to compare, but they remain materially different
  in probe fields, cost drivers, approval gates, and evidence layout. A generic reader would either
  leak video-specific knobs into text readers or hide real differences behind lowest-common-denominator
  types.

## Comparison (three reader shapes)

### Input discovery

| Concern | `video.py` | `image.py` | `article.py` |
|---|---|---|---|
| Local files | Any media path; `resolve_input` checks workspace inbox | File or folder; suffix or directory probe | `.html`, `.htm`, `.md`, `.markdown`, `.txt`, `.xml`, `.rss`, `.atom`; feed sniffing |
| URLs | `yt-dlp` metadata via `is_url` | Not supported | Non-video HTTP(S); video hosts excluded via `VIDEO_HOST_RE` |
| Routing in `voidscape.py` | Default after image and article checks | `_is_image_source` first | `_is_article_source` when not image |
| Symlinks | Allowed for video paths | Rejected at probe | Rejected at probe |

Image wins over article when a path is both a directory and could be misclassified; article wins
over video for non-video URLs.

### Probe metadata

| Field family | Video | Image | Article |
|---|---|---|---|
| Identity | `source`, `input`, `duration_s`, resolution, `has_audio` | `kind` (`image`/`carousel`), `item_count`, `images[]` | `kind` (`article`/`feed`/`article_url`), `entry_kind`, `item_count`, `entries[]` |
| Side signals | `sidecar_transcript`, `captions_available` | `skipped[]` (unsupported folder entries) | `feed_title`, `skipped[]`, `requires_fetch_approval` (URL probe only) |
| Limits surfaced | Implicit frame budget in estimate | `within_limit` (100 images) | `within_limit` (100 entries) |

Probe shapes intentionally differ: video is temporal + multimodal; image is ordered stills; article
is ordered text entries with citations.

### Estimates and cost drivers

| Concern | Video | Image | Article |
|---|---|---|---|
| Dominant drivers | Frame tokens, transcript tokens, transcription `$` | Image vision tokens | Text tokens (+ fixed overhead) |
| `cost_usd` keys | `transcription`, `agent`, `total` | Same shape; `transcription` always 0 | Same shape; `transcription` always 0 |
| Extra estimate knobs | `--tier`, `--backend`, `--frames`, `--transcribe-mode` | `--out-words`, `--agent-model` | `--out-words`, `--agent-model` |
| `free` semantics | `transcription_usd == 0` | Always local (`free: true`) | Local files free; URLs `free: false` until fetch approved |
| Shared math | `load_pricing`, `_agent_rate`, `per_frame_tokens` (image) | imports from `video` | imports from `video` |

### Approval and privacy gates

| Gate | Video | Image | Article |
|---|---|---|---|
| Cloud spend / upload | `requires_cloud_approval` when cloud transcription backends selected; `run --allow-cloud` | None — local copy only | `requires_fetch_approval` / `requires_cloud_approval` for remote URL fetch; `run --allow-fetch` / voidscape `--allow-cloud` |
| Model download | `needs_model_download` + `--allow-model-download` for faster-whisper | `not_applicable` | `not_applicable` |
| Dependency install | `needs_install` for missing local backends | ffprobe required | stdlib + urllib only |
| Browser credentials | Never read (yt-dlp cookies via env only) | N/A | Never read; paywall note in probe/estimate |

All gates remain **estimate-first, run-second**. `voidscape.py read` re-runs estimate before
`run` for video and article paths that need approval.

### Evidence output

| Artifact | Video | Image | Article |
|---|---|---|---|
| Workdir layout | `frames/`, optional `transcript.txt` | `images/` | `entries/` |
| Manifest | Frame list + timestamps, dedup count, transcript path | Ordered images with source names | Ordered entries with `citation_guide` |
| Citation style | `[MM:SS]` | `[image N]` | `[article N]` / `[entry N]` |
| Mutation model | Extract/transcode; may download URL media | Byte-preserving copy | Text copy with metadata header |

`manifest.json` is written only after successful evidence preparation in all three readers.

### Errors and agent CLI envelope

All three engines reuse `video._classify_error`, `video._envelope`, and `video._AgentArgumentParser`
for machine-readable failures. Exit codes are identical:

| Code | Meaning |
|---|---|
| 0 | success |
| 1 | unexpected_error |
| 2 | usage_error |
| 3 | input_error |
| 4 | approval_required |
| 5 | dependency_error |
| 6 | operation_failed |

`voidscape.py` routes all exceptions through `video._classify_error` for consistent JSON errors.

## Duplication inventory

### Worth keeping separate (reader-specific)

- Probe field schemas and validation (duration vs dimensions vs word counts).
- `run()` acquisition logic (ffmpeg/yt-dlp vs copy vs fetch/parse).
- Estimate driver breakdown and human `_fmt_estimate` strings.
- CLI flags beyond the shared output modes (`--tier` vs `--allow-fetch`).

### Already shared via `video.py` (sufficient)

- `{ok,data,error,meta}` envelope and compact JSON helpers.
- Error classification and agent argument parser behavior.
- Pricing load, agent model selection, per-frame token estimator (image).
- `resolve_input`, `is_url` (article routing).

### Parallel but not extracted (acceptable)

- Near-identical `main()` / `_cli_manifest()` / `_emit()` blocks in `image.py` and `article.py`
  mirror `video.py` but carry different command flags. Extracting a CLI factory saves lines, not
  conceptual complexity, and would couple all readers to one argparse builder.

## Alternatives considered

1. **No shared interface** — rejected. Agents and tests already depend on the manifest/envelope
   contract; undocumented parity would drift.
2. **Shared implementation layer** (base class or `reader_protocol.py` with generic `run`) —
   rejected. Would force artificial unification of probe/estimate/run payloads or grow a kitchen-sink
   options object. Past repo discipline (capture adapters, image reader) favors compare-then-extract.
3. **Small shared protocol only** — **chosen**. Document the contract; keep implementations focused;
   reuse `video.py` utilities where they are genuinely identical.

## Consequences

- Milestone 0.2 is **closed by documentation**, not by a new abstraction module.
- New media types (e.g. audio-only shortcut, PDF) should implement the same four commands and exit
  codes, then register discovery in `voidscape.py` — not subclass a generic reader.
- Phase 3.2 "how to build your own reader" should reference this spec as the contract checklist.
- Revisit extraction only if a **fourth** reader duplicates the same 50+ lines of CLI boilerplate
  *and* a new shared helper can be added without hiding real behavioral differences.

## Regression guard

`tests/test_media_reader_protocol.py` asserts the protocol parity and records the "no shared
implementation module" decision so it cannot silently regress.
