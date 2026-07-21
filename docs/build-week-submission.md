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

## 1:25 demo storyboard

The primary OpenScreen take is specified beat-by-beat in
[`demo-shot-list.md`](demo-shot-list.md):

- **0:00–0:08 — Payoff:** show one timestamp and its matching frame.
- **0:08–0:15 — Problem:** introduce the media people keep but cannot search.
- **0:15–0:25 — Inspect:** show source facts without processing or upload.
- **0:25–0:41 — Preview + GPT-5.6:** show patch estimation, tokens, cost, and the local path.
- **0:41–0:58 — Read:** produce and open frames, transcript, and manifest.
- **0:58–1:10 — Privacy proof:** show cloud audio rejected without `--allow-cloud`.
- **1:10–1:25 — Codex + provenance:** explain the concrete Codex contribution and separate the
  imported baseline from Build Week work.

Use only original screen and voiceover. The official submission requires a public YouTube video,
voiceover, a working demo, and specific explanations of Codex and GPT-5.6; keep it at or below
three minutes.

## Demand evidence

- [Request for Video-Watching Capabilities in ChatGPT](https://community.openai.com/t/request-for-video-watching-capabilities-in-chatgpt/1144152/19):
  5,146 views and 19 posts; OpenAI Support said direct video analysis was not fully supported in
  the requested form and logged the request.
- [Ability to write to Watch video from drop box](https://community.openai.com/t/ability-to-write-to-watch-video-from-drop-box/1387233):
  a user asked for a recorded video in a folder to be watched, heard, and turned into a report.

## Evidence and final human actions

- Run `/feedback` in the current end-to-end Codex session after the timestamp, installer,
  documentation, and browser-verification work is complete. Use the ID returned by `/feedback`,
  not an internal task/thread identifier.
- Manually compare fast/thorough transcripts on 2–3 original videos longer than 45 seconds.
- The release candidate passed an isolated dual-root install, fixture
  `inspect -> preview -> read`, and 154 tests. Repeat the critical path from a clean remote clone.
- Record/upload the public demo, add screenshots and the public repository URL, then **only submit
  when separately approved**.

## Production-readiness snapshot

| Item | Status | Current decision |
| --- | --- | --- |
| Analytics | N/A | No analytics or telemetry; keep the local-first release uninstrumented. |
| Public forms / bot protection | N/A | Static documentation site has no signup, contact, checkout, or upload form. |
| Privacy / data collection | Present for current scope | No accounts, hosted storage, or browser-cookie discovery. `SECURITY.md` documents local/cloud boundaries. Reassess policy and legal review before any hosted account product. |
| Operations | Present for current scope | No production backend to page or roll back; support and security reports route through the public issue tracker/maintainer. |
| Static security scan | Disclosed accepted risk | SkillSpector flags environment-key-to-provider requests, subprocesses, and external endpoints. These are documented and cloud audio remains blocked without `--allow-cloud`. |
| Public distribution | Present | The static site is served through Vercel at `https://voidscape.club`; browser verification covers the guide, FAQ, legal pages, repository, Security, and License links. |

The non-applicable and accepted-risk decisions above are advisory, not hidden launch blockers.
