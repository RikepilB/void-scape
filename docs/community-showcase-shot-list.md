# Demo shot list — Voidscape community showcase

- **Tool**: OpenScreen
- **Target total length**: 50-60 seconds
- **Date drafted**: 2026-07-20
- **Source file**: `docs/community-showcase-shot-list.md`
- **Format**: 16:9 MP4 for LinkedIn and WhatsApp; export a second vertical crop only if needed for X

## Pre-recording setup

```powershell
cd "<path-to-void-scape>"
python scripts/create-demo-fixture.py
python skill/scripts/voidscape.py read samples/build-week-demo.mp4 --tier both --backend captions --workdir samples/community-showcase-output
```

Open these before recording:

- `https://voidscape.club/`
- A terminal at the repository root with a large readable font
- `samples/community-showcase-output/transcript.txt`
- `samples/community-showcase-output/manifest.json`

## Beats

| # | Screen / state | Exact sequence | Narration | Target |
|---|---|---|---|---|
| 1 | Payoff first: transcript and one selected frame | Show `transcript.txt`, highlight one timestamp, then show its matching frame | "This answer comes from the video itself, with a timestamp you can verify." | 6s |
| 2 | Landing-page hero | Switch to the Voidscape page and hold on the headline | "I built Voidscape because I kept saving videos, then losing the useful moments inside them." | 7s |
| 3 | Inspect | In the terminal run `python skill/scripts/voidscape.py inspect samples/build-week-demo.mp4` | "First it inspects the source without processing it." | 7s |
| 4 | Preview gate | Run `python skill/scripts/voidscape.py preview samples/build-week-demo.mp4 --tier both --backend captions`; auto-zoom on cost, privacy, and approval fields | "Then it shows scope, cost, dependencies, and the privacy boundary before anything runs." | 12s |
| 5 | Read and artifacts | Run the prepared `read` command or replay its clean output, then show `frames/`, `transcript.txt`, and `manifest.json` | "After approval, it prepares frames, a timestamped transcript, and a manifest an AI agent can inspect." | 14s |
| 6 | Feedback invitation | Return to the landing page, then show the feedback-form title or QR code | "The prototype works. Now I need people to tell me where it is confusing and what would make it useful." | 8s |
| 7 | End card | Hold on the website and feedback URLs | "Try it, or watch the demo and share one honest improvement." | 5s |

## Recording notes

- Keep account names, browser tabs, cookies, local private paths, API keys, and personal media out of
  frame.
- Use the generated fixture, not private or copyrighted content.
- Use OpenScreen auto-zoom only on the preview fields and final timestamp. Too many zooms will make
  the terminal hard to follow.
- Add on-device captions after recording and listen once with sound off to verify the story still
  makes sense.
- After recording, review the MP4 with Voidscape against this shot list before publishing.
