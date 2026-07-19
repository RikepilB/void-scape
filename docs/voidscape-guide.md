# Voidscape guide

## The mental model

Voidscape has three deliberate moves:

1. **Inspect** — learn what the source contains without processing it.
2. **Preview** — see cost, privacy, dependencies, and consent requirements.
3. **Read** — prepare only the frames and transcript you approved, then let an agent answer from
   evidence with `[MM:SS]` citations.

This is not a video player or a black-box summary button. It produces inspectable artifacts so you
can understand what an agent used.

## Guided commands

Run these from the repository as `python skill/scripts/voidscape.py ...`, or from an installed
skill as `python scripts/voidscape.py ...`.

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
python skill/scripts/voidscape.py preview "demo.mp4" --tier visual

# A voice memo: local audio path.
python skill/scripts/voidscape.py preview "idea.m4a" --tier audio --backend faster-whisper

# A focused question around five minutes.
python skill/scripts/voidscape.py read "meeting.mp4" --start 270 --end 330 --workdir meeting-five-minutes
```

If a preview says cloud approval or a model download is required, stop and decide first. Add
`--allow-cloud` or `--allow-model-download` only after the user explicitly approved that exact
action.

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
```

The repository's Codex `/voidscape` router groups general media work and existing source
workflows. Instagram capture remains deliberately source-specific: it needs a signed-in browser,
an explicit watch confirmation for live actions, append-before-unsave protection, and its existing
subagents. Voidscape does not include a scheduler; Task Scheduler, cron, or an agent harness owns
the schedule and must carry the consent flags explicitly.

## Availability

| Capability | Status |
| --- | --- |
| Local recordings, videos, demos, and voice material | Available now |
| Supported public video URLs | Available now; platform access varies |
| Agent-readable frames, transcripts, manifest, and timestamp citations | Available now |
| Instagram saved-Reel capture | Available now in the repository's Codex workflow |
| Audio notes | Available now in the repository's Codex workflow |
| Private YouTube queue | Designed next |
| Substack/RSS articles and Markdown conversion | Planned; not a video-engine feature yet |
| Hosted product, universal extension, scheduled product workflows | Exploration only |
