# read-video import audit

Voidscape is built on Richard Pillaca's existing `read-video` work. This inventory records what the
fresh repository retained, what evolved after import, and what was intentionally not copied. It is
both a completeness check and evidence for the Build Week prior-work boundary.

## Retained product components

| Component | Voidscape path | Role |
| --- | --- | --- |
| Canonical media engine | `skill/scripts/video.py` | Probe, estimate, approval gates, frames, transcription, and manifests. |
| Guided CLI | `skill/scripts/voidscape.py` | `inspect -> preview -> read`, customization, and diagnostics. |
| Agent skill contract | `skill/SKILL.md` | Required consent and evidence-reading behavior. |
| Pricing and setup references | `skill/pricing.json`, `skill/references/`, `skill/workspace.example.json` | Cost model, backend guidance, and portable local configuration. |
| Legacy compatibility | `compat/read-video/` | Keeps existing `/read-video` callers working by forwarding to the canonical installed engine. |
| Dual-root installers | `scripts/install-skill.ps1`, `scripts/install-skill.sh` | Install Voidscape and compatibility skills for Codex and the shared agent root. |
| Reproducible demo | `scripts/create-demo-fixture.py` | Generates original, key-free media and captions for judge testing. |
| Optional Instagram helper | `scripts/instagram_capture_helper.py`, `.codex/agents/` | Repository-only, source-specific development workflow; not an installed Voidscape command. |
| Regression suite | `tests/` | Covers the engine, guided CLI, gates, timestamps, installer, fixture, helper, and documentation contracts. |
| License and attribution | `LICENSE`, `CREDITS.md` | Preserves MIT distribution and upstream prior-art credit. |

The compatibility `video.py` is intentionally a small forwarding shim rather than a copied engine.
That leaves one implementation of timestamp, privacy, backend, and error-handling behavior and
prevents the legacy command from drifting.

## Intentionally excluded

The migration does not copy artifacts that are private, generated, or unrelated to the distributable
product:

- `.env`, API keys, cookies, local `workspace.json`, and absolute machine configuration;
- `docs/handoff/`, transcripts, task briefs/reports, and session continuation scratch;
- scanner caches and lock files such as `.foglamp/`;
- generated demo videos, captions, evidence workdirs, and other reproducible output files.

Generated demo media is recreated with `python scripts/create-demo-fixture.py`. Private handoffs stay
available locally but are ignored by Git. A user-owned workspace or cookie export remains outside the
repository and is never treated as source code.

## Post-import evolution

The initial import is commit `fd4e47f`. Later commits and the current release work add or harden the
guided product, source-timeline citations, consent enforcement, installer verification, authenticated-
source guidance, and browser/CLI evidence. Git history is the source of truth for the split between
the imported baseline and later work.

## Verification

The retained parts are exercised together by the full test suite and the clean judge path:

```powershell
.\scripts\install-skill.ps1
python scripts/create-demo-fixture.py
python skill/scripts/voidscape.py inspect samples/build-week-demo.mp4
python skill/scripts/voidscape.py preview samples/build-week-demo.mp4 --tier both --backend captions
python skill/scripts/voidscape.py read samples/build-week-demo.mp4 --tier both --backend captions --workdir samples/build-week-output
```

The installer test also invokes the installed `read-video` facade and confirms it reaches the
canonical Voidscape manifest.
