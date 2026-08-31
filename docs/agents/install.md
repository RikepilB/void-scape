# Install Voidscape

Install one global CLI and its bundled agent skill. You do not need to clone the repository, create
an account, add an API key, or approve cloud processing.

## Open a terminal

On Windows, open **Start -> PowerShell**. On macOS or Linux, open the Terminal app.

## Install `uv` once

### Windows PowerShell

```powershell
winget install --id=astral-sh.uv -e
```

### macOS or Linux

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Skip this step if `uv --version` already works.

## Install the CLI and agent skill

```powershell
uv tool install https://github.com/RikepilB/void-scape/archive/refs/heads/main.zip
uv tool update-shell
voidscape init
```

`uv tool install` creates the global `voidscape` command in an isolated environment and installs
its `yt-dlp` dependency. `voidscape init` copies the primary skill into:

- `~/.codex/skills/voidscape` for Codex;
- `~/.agents/skills/voidscape` for shared agent discovery.

It preserves an existing local `workspace.json`, does not read API keys, and does not approve a
cloud job or model download. If `voidscape` is not recognized immediately after
`uv tool update-shell`, open one new terminal and run `voidscape init` there.

Use `voidscape init --no-skill` for a CLI-only setup. To update, add `--upgrade` to the
`uv tool install` command, then run `voidscape init` again.

## Verify readiness

Run the read-only diagnostic before using personal media:

```powershell
voidscape doctor
```

Doctor reports Python, FFmpeg, FFprobe, yt-dlp, workspace configuration, and optional local speech
support. It does not install a missing dependency or download a model.

If FFmpeg or FFprobe is missing, install the package for your platform:

```text
Windows:       winget install --id=Gyan.FFmpeg -e
macOS:         brew install ffmpeg
Debian/Ubuntu: sudo apt update && sudo apt install ffmpeg
```

| Tool | Required when |
| --- | --- |
| Python 3.10+ | Always |
| FFmpeg and FFprobe | Video, audio, screenshots, or short clips |
| yt-dlp | Supported public media URLs |
| faster-whisper | Local speech transcription without existing captions or sidecars |

## Configure local folders

Configuration is optional. Preview the values first; save only after explicit confirmation.

```powershell
voidscape customize
```

Voidscape stores local paths and local defaults, not API keys. A first model download and every
cloud transcription job remain separate decisions even when a default backend is configured.

## Read one file

Replace `meeting.mp4` with a local image, audio file, video, folder, or supported public URL:

```powershell
voidscape inspect "meeting.mp4"
voidscape preview "meeting.mp4"
voidscape read "meeting.mp4" --workdir voidscape-output
```

The final command can create `voidscape-output/manifest.json`, `transcript.txt`, and `frames/`.
The exact artifacts depend on the source and scope you approved.

## Ask your agent

Copy this prompt:

> Open `voidscape-output/manifest.json` and `transcript.txt`, then inspect `frames/`.
> Summarize the recording in three bullets. Support every factual claim with an exact `[MM:SS]`
> citation. If the evidence is insufficient, say so.

If an agent session that was already open does not show Voidscape, start a new agent session after
installation.

## Confirm the installed contract

Open the installed `SKILL.md` or run `voidscape` without arguments. The supported flow
must still read `inspect -> preview -> read`. If an install claims browser-cookie discovery,
automatic cloud use, or unattended approval flags, stop: that is not the Voidscape contract.

## Repository contributor proof

Cloning is only needed for development. Contributors can run `python scripts/create-demo-fixture.py`
from a source checkout to generate the copyright-free test fixture.

## Next

Continue to [Quick start](quick-start.md) for the meaning of each proof step, or
[Workflow and protocol](workflow.md) for real sources and approval fields.
