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
| Repository | https://github.com/RikepilB/read-video |
| Project URL | https://rikepilb.github.io/read-video/ |
| Built with | Python, Codex, GPT-5.6, FFmpeg, FFprobe, yt-dlp, faster-whisper, pytest |
| `/feedback` session ID | Pending — add only after the confirmed primary implementation session. |

## Project description

I built Voidscape because saved videos, voice notes, demos, and recordings keep becoming a pile of
things I mean to return to. An agent can summarize text and images, but it cannot actually inspect a
video file unless someone first turns that media into evidence it can read.

Voidscape is a local-first personal media workflow built on my open-source `read-video` engine. It
helps me move from a recording or video URL to selected frames, a timestamped transcript, and a
manifest that maps the evidence back to the source. An agent can then answer from those artifacts
with `[MM:SS]` citations instead of guessing from a title, thumbnail, or prompt.

The part I care about most is the decision before processing. Voidscape uses three simple moves:

1. **Inspect** the source: duration, audio, captions, sidecars, and likely scope.
2. **Preview** the cost, dependency, model-download, and cloud-privacy boundary.
3. **Read** only the approved media into frames, transcript, and manifest.

The default path stays local. A cloud transcription route is rejected unless I explicitly approve
`--allow-cloud`; a first-time local Whisper model download has its own separate approval. The
estimate also shows an API-equivalent GPT-5.6 vision-token cost before the agent reads frames.

I use it for personal research and productivity: reviewing a meeting or screen recording, turning a
voice memo into a Markdown note through an agent, and working through saved learning videos. The
repository also contains an optional, user-observed Instagram saved-Reel workflow that captures a
confirmed public URL before analysis. It is deliberately source-specific rather than pretending all
browser automation is safe or interchangeable.

### Built with Codex and GPT-5.6

Codex helped me audit the existing engine, implement the guided Voidscape layer, build tests, and
exercise the actual inspect → preview → consent → read flow. GPT-5.6 pricing is part of the gate:
the project estimates 32×32 vision patches and makes the dominant cost visible before the run.

The human choices stayed mine: local-first privacy, separate consent for cloud and model downloads,
the personal-media use cases, and the decision not to claim unbuilt adapters as product features.

### Available now

- Local recordings, demos, meetings, screen captures, voice material, and supported public video URLs.
- Local frames, transcripts, manifests, cost previews, and timestamp-grounded agent answers.
- Guided `inspect`, `preview`, `read`, `customize`, and `doctor` commands.
- Existing Instagram saved-Reel and audio-note workflows in the repository's Codex setup.

### Planned, not claimed as shipped

- Substack/RSS article intake and text-to-Markdown conversion.
- Private YouTube queue capture and additional source adapters.
- A scheduling product, universal browser extension, multi-model reader, and hosted service.

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
