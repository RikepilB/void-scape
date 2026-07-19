# OpenAI Build Week submission runbook

## Devpost-ready summary

**Voidscape** is a local-first personal media workflow powered by the open-source `read-video`
engine. It turns local recordings, demos, meetings, voice notes, and approved video URLs into
timestamped frames, transcripts, and manifests an agent can inspect. Before remote or paid work,
it makes the scope, estimated cost, privacy boundary, and required consent visible.

Category: **Apps for Your Life**. The public test path is to generate
`samples/build-week-demo.mp4`, then use the guided sequence:

```powershell
python scripts/create-demo-fixture.py
python skill/scripts/voidscape.py inspect samples/build-week-demo.mp4
python skill/scripts/voidscape.py preview samples/build-week-demo.mp4 --tier both --backend captions
python skill/scripts/voidscape.py read samples/build-week-demo.mp4 --tier both --backend captions --workdir samples/build-week-output
```

The lower-level `video.py` commands remain available for automation and judge troubleshooting.

## 2:40 demo storyboard

- **0:00–0:20 — Problem:** personal recordings and saved learning media are easy to lose; an agent
  should work from the footage, not a title or a guess.
- **0:20–0:45 — Install + fixture:** install the dual Voidscape/read-video skill and create the
  original local fixture. State that no key or copyrighted media is needed.
- **0:45–1:15 — Inspect + preview:** show source facts, the chosen scope, patch-token accounting,
  API-equivalent cost, local dependency status, and privacy/approval fields.
- **1:15–1:40 — Read + result:** run the local path and have Codex answer from the resulting frames
  and transcript with `[MM:SS]` citations.
- **1:40–2:05 — Local transcription:** on an original spoken clip, compare fast and thorough local
  transcription and show that the user chooses the scope before reading.
- **2:05–2:25 — Privacy proof:** try a cloud fallback without `--allow-cloud` and show rejection
  before audio conversion or upload.
- **2:25–2:40 — Collaboration + impact:** explain how Codex and GPT-5.6 accelerated the guided
  interface and testing, while human decisions set cost, privacy, and source boundaries.

Use only original screen and audio. Keep the public YouTube video under three minutes.

## Evidence and final human actions

- Implementation Codex task: `019f708e-5615-7f00-9a02-b0e5bc435efd`.
- Run `/feedback` in the primary end-to-end Codex task and paste the returned session ID into
  Devpost.
- Manually compare fast/thorough transcripts on 2–3 original videos longer than 45 seconds.
- Test from a clean clone, record/upload the public demo, add screenshots and the public repository
  URL, then **only submit when separately approved**.
