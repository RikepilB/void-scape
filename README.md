# Voidscape

**Turn media you keep into local, timestamped evidence an agent can use.**

Voidscape is the guided product layer for the open-source `read-video` engine. Give it a local
recording or supported video URL and it prepares frames, a transcript, and a manifest an agent can
inspect. Before anything paid, remote, or first-time-heavy happens, you see the cost and privacy
gate.

`read-video` remains the stable engine and compatibility name for existing scripts and automations.

> Status: local videos, recordings, voice material, public video URLs, and the Instagram capture
> workflow are available today. Substack/RSS intake, scheduled workflows, universal capture, and a
> hosted product are planned—not shipped.

## Start here

Run either installed command without arguments for a short Voidscape welcome screen and the next
command to try. The old `read-video` entry keeps its existing command behavior; its no-command
screen now points into the guided Voidscape flow.

### 1. Install both Voidscape and the read-video compatibility skill

**Windows PowerShell**

```powershell
.\scripts\install-skill.ps1
```

**macOS / Linux / Git Bash**

```bash
bash scripts/install-skill.sh
```

The installer creates the new `voidscape` skill and keeps `read-video` available for existing
automations. It never overwrites a local `workspace.json` or reads API keys.

### 2. Optional: choose where your media and notes live

Run this from the installed Voidscape skill, or use the repository path shown below:

```powershell
# Interactive: preview your settings, then confirm before saving.
python skill/scripts/voidscape.py customize

# Reuse an existing read-video workspace after reviewing the import.
python skill/scripts/voidscape.py customize --import-read-video --yes
```

`customize` stores only local folders and local defaults: Inbox, Library, transcription backend,
Whisper model, and the long-audio threshold. It never stores API keys. Use `--create-dirs` when you
want it to create missing Inbox or Library folders.

### 3. Inspect, preview, then read

```powershell
python skill/scripts/voidscape.py inspect "meeting.mp4"
python skill/scripts/voidscape.py preview "meeting.mp4"
python skill/scripts/voidscape.py read "meeting.mp4" --workdir out
```

`inspect` is free source discovery. `preview` shows cost, dependencies, model-download state, and
whether audio would leave your machine. `read` prepares the approved `frames/`, `transcript.txt`,
and `manifest.json` artifacts. Then ask your agent to use them and cite moments as `[MM:SS]`.

For a reproducible, key-free first run:

```powershell
python scripts/create-demo-fixture.py
python skill/scripts/voidscape.py inspect samples/build-week-demo.mp4
python skill/scripts/voidscape.py preview samples/build-week-demo.mp4 --tier both --backend captions
python skill/scripts/voidscape.py read samples/build-week-demo.mp4 --tier both --backend captions --workdir samples/build-week-output
```

## Use it with an agent

After install, use `/voidscape <file-or-url>` in an agent harness that exposes skills as slash
commands, or simply ask the agent to inspect, preview, and read your media with Voidscape. The
agent should:

1. inspect the source;
2. preview the selected scope;
3. stop for explicit consent when cloud processing or a model download is required;
4. read the resulting artifacts and answer with timestamp citations.

The repository's Codex router also supports `/voidscape inspect`, `preview`, `read`,
`customize`, `doctor`, `capture instagram`, `process instagram`, and `audio`. Existing
`/read-video`, `/instagram-capture`, `/ig-pipeline`, and `/read-audio` commands still work.

## Choose the right path

| Need | Use | What happens |
| --- | --- | --- |
| Understand a local recording, demo, meeting, or screen capture | `inspect → preview → read` | Frames, transcript, and manifest stay local by default. |
| Save a voice memo or call as a searchable note | `/voidscape audio ...` | Existing audio workflow transcribes locally, then an agent writes the Markdown note. |
| Turn saved Instagram learning Reels into research | `/voidscape capture instagram` then `process instagram` | Codex-only, user-observed capture queue and source-specific analysis workflow. |
| Run from an agent, hook, or schedule | `voidscape.py ... --json` or raw `video.py ... --envelope --compact` | Non-interactive commands; Voidscape does not ship a scheduler. |
| Read a Substack series or RSS feed | Planned | Text/RSS ingestion is not part of the video engine yet. |

## Typical questions

### Does Voidscape upload my media?

Not by default. Local files, sidecar subtitles, and local transcription stay on your machine. Any
cloud transcription path is blocked until you explicitly add `--allow-cloud`. A first-time local
Whisper model download separately needs `--allow-model-download`.

### What does it cost?

`preview` estimates transcription and API-equivalent agent-token cost before `read`. The estimate
also explains the dominant cost, backend chain, local dependency, and approval state. A Codex
subscription may not bill per API token; the GPT-5.6 amount is an honest comparison estimate.

### What files are created?

`read` creates a temporary or chosen work folder with `frames/`, `transcript.txt`, and
`manifest.json`. The agent uses those as evidence. When a workspace is configured, the agent
workflow can save its final answer as a Markdown note in your Library; the engine itself does not
pretend to author the note.

### What is the difference between `read` and `read-video`?

Voidscape is the guided name and product experience. `read-video` is the underlying, stable CLI and
legacy installed skill. Existing scripts keep using raw `video.py`; new users should start with
Voidscape.

### Can I automate it?

Yes. Use `customize` with flags and `--yes`, then call `voidscape.py` with explicit flags and
`--json`, or call the raw engine with `--envelope --compact`. Use your own Task Scheduler, cron, or
agent hook. Review cloud and model-download consent in the job definition; Voidscape never assumes
it.

## Advanced engine interface

For scripts, subagents, and integrations, the raw engine remains stable:

```powershell
python skill/scripts/video.py manifest --compact
python skill/scripts/video.py probe "clip.mp4" --envelope --compact
python skill/scripts/video.py estimate "clip.mp4" --tier both --backend captions --envelope --compact
python skill/scripts/video.py run "clip.mp4" --tier both --backend captions --workdir out --envelope --compact
```

The envelope is `{ok,data,error,meta}` with deterministic error codes and retryability metadata.
See the [guided workflow and automation guide](docs/voidscape-guide.md),
[advanced CLI reference](docs/cli-reference.md), and [privacy/backend notes](skill/references/backends.md).

## Requirements

- Python 3.10+
- `ffmpeg` and `ffprobe` on `PATH`
- `yt-dlp` only for URLs
- `faster-whisper` only for local speech transcription

Run `python skill/scripts/voidscape.py doctor` to see what is ready without changing anything.

## Build Week evidence

Voidscape was built with Codex and GPT-5.6 on top of the `read-video` engine. The Build Week work
adds GPT-5.6 32×32 patch estimates, adaptive local transcription, explicit cloud/model-download
consent enforcement, a reproducible fixture, and an opt-in agent protocol. See the
[submission runbook](docs/build-week-submission.md) and [project draft](docs/devpost-draft.md).

## License

[MIT](LICENSE) © Richard Pillaca.
