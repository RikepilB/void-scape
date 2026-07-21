# Demo shot list — Voidscape (OpenAI Build Week 2026)

- **Tool**: OpenScreen
- **Target total length**: 85 seconds
- **Date revised**: 2026-07-20
- **Source file**: `docs/demo-shot-list.md`
- **Format**: 16:9, 1080p, English voiceover, MP4
- **Submission requirement**: show the working project and explain specifically how Codex and
  GPT-5.6 were used. Do not cut beats 4 or 7.

This is the primary judge cut. The separate 59-second community-feedback cut remains in
`docs/community-showcase-shot-list.md`.

## Pre-recording setup

Use a clean PowerShell window at the repository root. Increase the terminal font until one command
and its output remain readable at 1080p. Close private tabs, notifications, API-key terminals, and
personal media.

Run before recording:

```powershell
python scripts/create-demo-fixture.py
Copy-Item samples/build-week-demo.mp4 samples/privacy-proof.mp4
```

The copied file has no matching sidecar transcript, so the final cloud command reaches the consent
gate. Use fresh workdir names for every take; Voidscape deliberately rejects non-empty evidence
folders.

Prepare these tabs/windows:

1. `https://voidscape.club`
2. PowerShell at the repository root
3. File Explorer open to the fresh evidence workdir
4. README at “Built with Codex” and `docs/BUILD_WEEK_PROVENANCE.md`

## Beats

| # | Screen / state | Exact sequence | Voiceover | Target |
|---|---|---|---|---|
| 1 | Payoff first: one selected frame beside `transcript.txt` | Open a prepared evidence folder. Highlight `[00:04]`, then show the matching frame. | “Voidscape turns a video an AI agent cannot inspect into frames, timestamped text, and a manifest it can verify.” | 8s |
| 2 | Landing-page hero | Switch to `voidscape.club`; hold on “Make the media you keep legible.” | “I built it for the recordings, demos, and saved videos that are useful but hard to search.” | 7s |
| 3 | Guided inspect | Run `python skill/scripts/voidscape.py inspect samples/build-week-demo.mp4`. Auto-zoom once on duration, audio, sidecar, and suggested scope. | “Inspect discovers what is present without processing or uploading the source.” | 10s |
| 4 | Guided preview — GPT-5.6 integration | Run `python skill/scripts/voidscape.py preview samples/build-week-demo.mp4 --tier both --backend captions`. Hold on `agent=gpt-5.6-terra`, `vision=openai_patch32`, token counts, cost, and the local-next-step line. | “Preview prices the job before it runs. GPT-5.6 reads the selected evidence, and Voidscape estimates its 32-by-32 vision patches so scope and API-equivalent cost are visible first.” | 16s |
| 5 | Read and inspectable artifacts | Run `python skill/scripts/voidscape.py read samples/build-week-demo.mp4 --tier both --backend captions --workdir samples/build-week-output-take1`. Switch to File Explorer and open `frames/`, `transcript.txt`, and `manifest.json`. | “Read prepares only the approved evidence. Here it stays local and free, and an agent can answer from the source timeline instead of guessing from a title.” | 17s |
| 6 | Privacy proof | Run `python skill/scripts/voidscape.py read samples/privacy-proof.mp4 --tier audio --backend openai --workdir samples/privacy-proof-output-take1` without `--allow-cloud`. Hold on the rejection. | “A cloud backend is blocked before conversion or upload. A key is never consent; cloud transfer and local model downloads have separate approval gates.” | 12s |
| 7 | Codex contribution, provenance, close | Show README “Built with Codex,” then `BUILD_WEEK_PROVENANCE.md`, ending on the current GitHub URL. | “I chose the local-first boundary and inspect-preview-read flow. During Build Week, Codex audited my existing engine, found timestamp and installer defects, added regression coverage, and helped make the judge path reproducible. The imported baseline and new work are separated in the repo.” | 15s |

**Total: 85 seconds.**

## OpenScreen edit instructions

- Use one auto-zoom on beat 3 and one on beat 4; add a manual zoom for the rejection in beat 6.
- Set each zoom long enough to read the highlighted fields; avoid cursor-follow zoom while commands
  are printing.
- Trim command-entry pauses, but keep at least a one-second hold after every result.
- Smooth the cursor path between `frames/`, `transcript.txt`, and `manifest.json`.
- Add on-device English captions and manually correct `Voidscape`, `Codex`, `GPT-5.6`,
  `FFmpeg`, and flag names.
- Use a restrained dark gradient background and no more than one annotation: an arrow pointing to
  the consent rejection.
- Export MP4 at 1080p, 30 fps, 16:9, with no watermark.

## Capture rules

- Narration is required. A music-only screencast is not eligible.
- Keep the video in English, or add an English translation to the submission.
- Do not show browser cookies, environment variables, account names, private paths, API keys,
  personal media, or unrelated tabs.
- Do not claim roadmap items as shipped. The demo covers only local/public media evidence,
  inspect/preview/read, GPT-5.6 cost estimation, artifacts, and consent gates.
- Do not show the old `read-video` repository or Pages URL. End on
  `https://github.com/RikepilB/void-scape` and use `https://voidscape.club` as the product URL.

## Review pass after recording

The human records and edits the video in OpenScreen; this workflow does not automate the GUI or
modify the video file. After export, review the MP4 with Voidscape:

```powershell
python skill/scripts/voidscape.py inspect "PATH\TO\voidscape-demo.mp4"
python skill/scripts/voidscape.py preview "PATH\TO\voidscape-demo.mp4" --tier both --backend faster-whisper
```

Because this submission requires voiceover, use `both` for the final review. If preview reports a
first-time model download, stop and decide before adding `--allow-model-download`. Then read into
a fresh workdir and compare every beat against this table. The review output should be a concrete
OpenScreen edit list; it must not alter the video automatically.

## Final checklist

- [ ] 85 seconds or shorter; comfortably below the official 3-minute limit.
- [ ] Public YouTube upload.
- [ ] English voiceover is clear with captions enabled.
- [ ] Working inspect, preview, read, artifacts, and privacy rejection are visible.
- [ ] Codex contribution is specific, not decorative.
- [ ] GPT-5.6 integration and patch estimator are visible and explained.
- [ ] Current website and GitHub URLs appear in the end card/description.
- [ ] No secrets, personal content, or unsupported roadmap claims are visible.
