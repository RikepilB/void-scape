# Demo shot list — read-video (OpenAI Build Week 2026 submission)

- **Tool**: OpenScreen (CLI/terminal demo — cinematic zoom on the JSON output is the whole point)
- **Target total length**: ~2:40 (Devpost hard cap: under 3:00)
- **Date drafted**: 2026-07-17
- **Source file**: `docs/demo-shot-list.md`
- **Devpost requirement**: narration must cover how **both** Codex and GPT-5.6 were used — beats
  6 and 7 carry that explicitly, don't cut them for time.

## Pre-recording setup (do once, before hitting record)

```powershell
cd read-video
python scripts/create-demo-fixture.py                       # samples/build-week-demo.mp4 + .srt
Copy-Item samples/build-week-demo.mp4 samples/privacy-proof.mp4   # no sidecar -> actually triggers the cloud gate
```
Also have ready: **one real spoken audio/video clip you own, longer than 45 seconds** (a voice
memo, a recorded call, anything with actual speech) for beat 5 — the synthetic fixture has no
real speech, so it can't demonstrate the fast/thorough transcription difference. Do not use
anything copyrighted or containing someone else's likeness without consent.

## Beats

| # | Screen / state | Click sequence / command | Narration line | Target duration |
|---|---|---|---|---|
| 1 | Terminal, empty prompt | (talking head or terminal only) | "Coding agents can read images and text. They can't watch video — and when a tool bolts that on, it usually hides two things: what it costs, and whether your audio just left the machine." | 20s |
| 2 | Terminal, repo root | `.\scripts\install-skill.ps1` then `python scripts/create-demo-fixture.py` | "One-command install into Codex or Codex. This fixture is generated locally — no API key, no copyrighted media, reproducible by any judge." | 25s |
| 3 | Terminal, estimate output | `python skill/scripts/video.py estimate samples/build-week-demo.mp4 --tier both --backend captions --agent-model gpt-5.6-terra --human` — let the JSON/table sit on screen, zoom into `cost_usd`, `agent_model`, `vision_estimator`, `model_download` | "Before anything runs, estimate prices the whole job — GPT-5.6's real 32×32 patch accounting, not a rough guess — and tells you if a model needs downloading or a backend needs approval. This is the gate: nothing spends or leaves the machine past this point without you saying so." | 30s |
| 4 | Terminal, run output → Codex reading frames | `python skill/scripts/video.py run samples/build-week-demo.mp4 --tier both --backend captions --workdir samples/build-week-output`, then have Codex read the manifest/frames/transcript and answer a question with `[MM:SS]` citations | "Approved, it runs locally and free. Codex reads the frames and the sidecar transcript and answers grounded in the actual timestamps — not a hallucinated summary." | 25s |
| 5 | Terminal, two transcript runs side by side | `python skill/scripts/video.py run <your-real-clip> --transcribe-mode fast --workdir out-fast` then `--transcribe-mode thorough --workdir out-thorough`; scroll both transcripts | "On real speech past 45 seconds, thorough mode switches to a bigger model, tunes the VAD, and drops previous-text conditioning — you can see the difference on the same clip." | 25s |
| 6 | Terminal, rejected run | `python skill/scripts/video.py run samples/privacy-proof.mp4 --tier audio --backend openai` (no `--allow-cloud`) — let the `PermissionError` sit on screen | "And this is the boundary that actually matters: a cloud backend in the chain gets rejected before the file is even converted to audio — an API key sitting in your environment is never treated as consent. That gate, the GPT-5.6 patch-token accounting, and the adaptive transcription tiers were all built and tested inside Codex this week." | 25s |
| 7 | Talking head or terminal + browser tab on the GitHub repo | Show repo / README / SECURITY.md briefly | "Codex implemented the gate logic, the pricing math, and the test suite end to end; the calls on where to draw the line — the 45-second threshold, local-first by default, how conservative the fallback pricing should be — were mine. Full breakdown is in the repo." | 20s |
| 8 | Landing page (rikepilb.github.io/read-video) scrolled to case files | Scroll past hero, pause on the two case-file cards | "It's not a demo toy — it's already processed over a hundred real videos into a personal knowledge base, and helped pick a real hackathon project from a voice memo." | 15s |
| 9 | GitHub repo root | End on repo URL + license badge | "MIT-licensed, link in the description." | 5s |

## Notes

- Beats are ordered by narrative (problem → gate → payoff → privacy proof → collaboration →
  impact → close), not by CLI subcommand order.
- Beat 6 depends on the **pre-recording setup**'s `privacy-proof.mp4` copy — the main fixture has
  a sidecar transcript and will NOT trigger the gate (verified; this was a real bug caught and
  fixed in this same branch — see `docs/build-week-submission.md`'s evidence section).
- Beat 5 needs a real spoken clip the presenter owns — not the synthetic fixture. If none is ready
  by recording time, cut beat 5 and redistribute its 25s across beats 3/4/6 rather than delaying
  the whole recording — the Devpost deadline doesn't move.
- Keep narration lines close to verbatim above; they were written to hit both "Codex" and
  "GPT-5.6" usage explicitly, which Devpost's submission requirements call out by name.
- After recording, review with `read-video --tier visual` against this table beat-by-beat before
  calling it done — silent screen-only pass is enough to check pacing/coverage; audio narration
  quality is a separate manual listen.
