# Install Voidscape

Install the Voidscape skill, keep the compatibility command available, and verify the local tools
you actually plan to use. The installer does not read API keys or overwrite local workspace choices.

## Install the skill

From the repository root, run the command for your platform.

### Windows PowerShell

```powershell
.\scripts\install-skill.ps1
```

### macOS, Linux, or Git Bash

```bash
bash scripts/install-skill.sh
```

The installer copies the supported `voidscape` skill and keeps the documented `read-video`
compatibility entry. New workflows should start with Voidscape.

## Verify readiness

Run the read-only diagnostic before using personal media:

```powershell
python skill/scripts/voidscape.py doctor
```

Doctor reports Python, FFmpeg, FFprobe, yt-dlp, workspace configuration, and optional local speech
support. It does not install a missing dependency or download a model.

| Tool | Required when |
| --- | --- |
| Python 3.10+ | Always |
| FFmpeg and FFprobe | Video, audio, screenshots, or short clips |
| yt-dlp | Supported public media URLs |
| faster-whisper | Local speech transcription without existing captions or sidecars |

## Configure local folders

Configuration is optional. Preview the values first; save only after explicit confirmation.

```powershell
python skill/scripts/voidscape.py customize
```

Voidscape stores local paths and local defaults, not API keys. A first model download and every
cloud transcription job remain separate decisions even when a default backend is configured.

## Confirm the installed contract

Open the installed `SKILL.md` or run the repository command without arguments. The supported flow
must still read `inspect -> preview -> read`. If an install claims browser-cookie discovery,
automatic cloud use, or unattended approval flags, stop: that is not the Voidscape contract.

## Next

Continue to [Quick start](quick-start.md) for a reproducible first read with no personal source and
no paid backend.
