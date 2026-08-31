# Voidscape guide

## The mental model

Voidscape has three deliberate moves:

1. **Inspect** — learn what the source contains without processing it.
2. **Preview** — see cost, privacy, dependencies, and consent requirements.
3. **Read** — prepare only the evidence you approved, then let an agent answer with `[MM:SS]`
   citations for video or `[image 1]` for local image/carousel evidence.

This is not a video player or a black-box summary button. It produces inspectable artifacts so you
can understand what an agent used.

## Guided commands

Run these from any terminal with the installed `voidscape` command.

| Command | Use it when | Changes media or configuration? |
| --- | --- | --- |
| `inspect <input>` | You need source facts and a recommended scope. | No |
| `preview <input>` | You need the price/privacy/dependency gate. | No |
| `read <input>` | You approved the path and want evidence artifacts. | Creates the selected work folder only. |
| `customize` | You want local folders and defaults. | Preview by default; writes only with `--yes`. |
| `doctor` | You want to check readiness. | No |

### Useful examples

```powershell
# A screen recording: visual evidence first.
voidscape preview "demo.mp4" --tier visual

# A voice memo: local audio path.
voidscape preview "idea.m4a" --tier audio --backend faster-whisper

# A focused question around five minutes.
voidscape read "meeting.mp4" --start 270 --end 330 --workdir meeting-five-minutes

# One local folder becomes one filename-ordered carousel evidence bundle.
voidscape inspect "slides"
voidscape preview "slides"
voidscape read "slides" --workdir slide-evidence
```

Image folders are local and non-recursive, accept JPG/JPEG, PNG, and WebP, and are capped at
100 images. Voidscape copies original bytes without renaming or changing the source files.

If a preview says cloud approval or a model download is required, stop and decide first. Add
`--allow-cloud` or `--allow-model-download` only after the user explicitly approved that exact
action.

## Public URLs and signed-in sources

Local files and public media URLs are the reproducible baseline. Voidscape began as Richard's
personal workflow for media in accounts where he was already signed in, but those private folders
and sessions are test inputs, not global defaults.

For an account-only source, the user signs in themselves and controls all access. A browser-connected
agent can help select an item after explicit site approval. The media CLI needs its own optional
Netscape cookie export through `READ_VIDEO_YTDLP_COOKIES`; browser access is not automatically shared
with `yt-dlp`. See [Public and authenticated sources](authenticated-sources.md) for the safe setup,
Chrome requirements, VPN troubleshooting, and current limitations.

## Customize and import

`customize` writes a local `workspace.json` next to the installed Voidscape skill. Its settings are
portable paths and defaults, never credentials.

```powershell
# Review a legacy read-video workspace; no changes yet.
python scripts/voidscape.py customize --import-read-video

# Save explicit folders for a non-interactive setup.
python scripts/voidscape.py customize --inbox "D:\Media\Inbox" --library "D:\Notes\Voidscape" --backend captions --create-dirs --yes
```

The legacy `read-video` facade keeps using its own existing `workspace.json`. Importing is explicit
so no old automation changes configuration silently.

## Agents, subagents, and schedules

For a person, use `/voidscape <input>` or ask the agent to use Voidscape. For an automation, use
the raw engine's stable JSON envelope:

```powershell
python scripts/video.py estimate "clip.mp4" --tier both --backend captions --envelope --compact
python scripts/image.py manifest --compact
python scripts/image.py estimate "slides" --envelope --compact
```

The installed Voidscape skill teaches an agent the guided commands above; the concrete interface is
`python scripts/voidscape.py ...`. Repository-only helpers and source-specific Codex agents are
development surfaces, not installed `/voidscape` subcommands. Instagram capture remains deliberately
source-specific: it needs a signed-in browser, explicit confirmation for live actions, and
append-before-unsave protection. Voidscape does not include a scheduler; Task Scheduler, cron, or an
agent harness owns the schedule and must carry the consent flags explicitly.

## Availability

| Capability | Status |
| --- | --- |
| Local recordings, videos, demos, and voice material | Available now |
| Local images and filename-ordered carousel folders | Available now; non-recursive and capped at 100 images |
| Supported public video URLs | Available now; platform access varies |
| Agent-readable frames, transcripts, manifest, and timestamp citations | Available now |
| Instagram saved-Reel capture | User-observed repository workflow; requires the user's signed-in Chrome session and is not an installed command |
| Audio-only reads | Available now through the installed CLI; an agent can author a note from the resulting evidence |
| Private YouTube queue | Designed next |
| Substack/RSS articles and Markdown conversion | Planned; not a video-engine feature yet |
| Hosted product, universal extension, scheduled product workflows | Exploration only |
