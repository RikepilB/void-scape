# Devpost project-page draft — Voidscape

Working copy for Devpost project `1332780`. Update the editable project page only. Do **not** submit
the Build Week entry until the public demo, `/feedback` ID, screenshots, and final human review are
complete.

## Project fields

| Field | Value |
| --- | --- |
| Name | **Voidscape** |
| Tagline | Turn the media you keep into local, timestamped evidence before you pay or upload. |
| Category | **Apps for Your Life** |
| Repository | https://github.com/RikepilB/void-scape |
| Project URL | https://voidscape.club |
| Built with | Python, Codex, GPT-5.6, FFmpeg, FFprobe, yt-dlp, faster-whisper, pytest |
| `/feedback` session ID | Pending — add only after the confirmed primary implementation session. |

## Project description

I built Voidscape because saved videos, voice notes, demos, and recordings keep becoming a pile of
things I mean to return to. An agent can summarize text and images, but it cannot actually inspect a
video file unless someone first turns that media into evidence it can read.

Voidscape is a local-first personal media workflow built on my open-source `read-video` engine.
Transcription is one channel, not the finished product: it combines selected frames, timestamped
text, and a manifest that maps the evidence back to the source. An agent can then answer from those
artifacts with `[MM:SS]` citations instead of guessing from a title, thumbnail, or prompt.

That is the product boundary. Specialist transcription tools are useful before Voidscape too: a
matching SRT, VTT, or text transcript can be reused as a free local sidecar. Voidscape focuses on
the governed handoff from media to an agent—scope, cost, consent, visual evidence, source timing,
and machine-readable failure handling.

The part I care about most is the decision before processing. Voidscape uses three simple moves:

1. **Inspect** the source: duration, audio, captions, sidecars, and likely scope.
2. **Preview** the cost, dependency, model-download, and cloud-privacy boundary.
3. **Read** only the approved media into frames, transcript, and manifest.

The default path stays local. A cloud transcription route is rejected unless I explicitly approve
`--allow-cloud`; a first-time local Whisper model download has its own separate approval. The
estimate also shows an API-equivalent GPT-5.6 vision-token cost before the agent reads frames.

I first built it for my own research: reviewing recordings, transcribing voice material, and working
through learning videos saved in accounts where I was already signed in. That personal setup is test
coverage, not the product's source of truth. The reproducible baseline is a local file or public
media URL. Account-only sources require the user's own login and explicit browser/site permission;
the current CLI can optionally use a user-exported cookie file, while a future product can replace
that bridge with revocable provider connections.

The repository also contains an optional, user-observed Instagram saved-Reel workflow that captures
a confirmed URL before analysis. That helper is repository-only, not an installed Voidscape command,
and is deliberately source-specific rather than pretending all browser automation is safe or
interchangeable.

The demand is visible without inventing a market claim. A March 2025 OpenAI Developer Community
thread requesting direct video analysis reached 5,146 views and 19 posts by April 2026. OpenAI
Support replied that it was [“not ... fully supported today in the way you're describing”](https://community.openai.com/t/request-for-video-watching-capabilities-in-chatgpt/1144152/19)
and said the request had been logged. In a separate July 2026 request, a user described wanting to
[“record a video, add it to Dropbox, and then direct my chat GPT assistant to the folder to watch,
listen to, and give a report”](https://community.openai.com/t/ability-to-write-to-watch-video-from-drop-box/1387233)—almost
exactly Voidscape's local Inbox-to-evidence workflow.

### Built with Codex and GPT-5.6

I brought the problem, the existing open-source engine, and the product decisions: local-first
privacy, explicit `inspect → preview → read`, separate consent for cloud transfer and model
downloads, source-timeline citations, the personal-media use cases, and the decision to defer
unattended orchestration. Codex accelerated the migration into a clean repository, audited claims
against the installed package, found the scoped-timestamp defect, wrote regression tests and fixes,
and hardened the reproducible judge path.

GPT-5.6 is used as the target agent model that reads the selected frames and transcript after the
gate. Voidscape estimates its 32×32 vision-patch input before that read, so model cost is visible at
the decision point. The dated import commit separates prior work from the post-import Build Week
changes judges should score.

### Available now

- Local recordings, demos, meetings, screen captures, voice material, and supported public video URLs.
- Local frames, transcripts, manifests, cost previews, and timestamp-grounded agent answers.
- Matching SRT, VTT, and plain-text sidecars, reused locally without retranscription.
- Visual, audio-only, or combined reads, including scoped time windows on the source timeline.
- A machine-readable envelope protocol, discovery manifest, and stable exit codes for agents.
- Guided `inspect`, `preview`, `read`, `customize`, and `doctor` commands.
- Audio-only reads through the same installed CLI.
- A repository-only Instagram URL validation/dedup helper, clearly labeled as not installed.
- A documented optional authentication bridge for user-owned sessions; cookies remain local and are
  never discovered by Voidscape.

### Planned, not claimed as shipped

- Substack/RSS article intake and text-to-Markdown conversion.
- Private YouTube queue capture and additional source adapters.
- A scheduling product, universal browser extension, multi-model reader, and hosted service.
- First-party OAuth/account connections with reviewable scopes and revocation.

## Judge test path

Supported: Windows PowerShell, macOS/Linux Bash, Python 3.10+, `ffmpeg`/`ffprobe`; `yt-dlp` only
for URLs. No key, account, or copyrighted media is required for this test.

```powershell
.\scripts\install-skill.ps1
python scripts/create-demo-fixture.py
python skill/scripts/voidscape.py inspect samples/build-week-demo.mp4
python skill/scripts/voidscape.py preview samples/build-week-demo.mp4 --tier both --backend captions
python skill/scripts/voidscape.py read samples/build-week-demo.mp4 --tier both --backend captions --workdir samples/build-week-output
```

Open `samples/build-week-output/manifest.json`, its frames, and `transcript.txt`, then ask an agent
for a summary with `[MM:SS]` citations. For the advanced machine protocol, use the existing raw
`video.py manifest --compact` and `--envelope --compact` commands documented in the repository.

## Before final submission

- Run the clean-clone test after the Voidscape install changes.
- Add the confirmed `/feedback` session ID.
- Record and upload the public under-three-minute YouTube demo with Richard's own voice.
- Add final thumbnail and screenshots.
- Review all Devpost fields and explicitly authorize the final submission.
