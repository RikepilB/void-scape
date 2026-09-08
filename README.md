# Voidscape

[Website](https://voidscape.club) ·
[GitHub repository](https://github.com/RikepilB/void-scape) ·
[Agent documentation](docs/agents/index.md)

**Turn media you keep into local, ordered evidence an agent can use.**

Transcription is one channel, not the finished product. Give Voidscape local images, a carousel
folder, a recording, or a supported video URL and it prepares ordered visual evidence, timestamped
text when relevant, and a manifest an agent can inspect. Before anything paid, remote, or
first-time-heavy happens, you see the cost and privacy gate.

Voidscape is the guided product layer for the open-source `read-video` engine. Its focus is the
decision and evidence boundary around an agent read: inspect the source, preview cost and consent,
then create only the approved artifacts. A matching `.srt`, `.vtt`, or `.txt` transcript can be
reused as a free local sidecar instead of being generated again.

`read-video` remains the stable engine and compatibility name for existing scripts and automations.

**Watch it work:** a 52-second terminal recording of the real flow —
[`doctor` → `inspect` → `preview` → `read` on the key-free demo fixture](docs/assets/cli-demo.mp4)
(no account, no API key, recorded live). The same video is embedded in the
[guide](https://voidscape.club/guide.html).

## Start here

You do not need to clone this repository. Install the CLI once, let it add the bundled agent skill,
then use `voidscape` from any terminal.

### 1. Install `uv` once

**Windows PowerShell**

```powershell
winget install --id=astral-sh.uv -e
```

**macOS / Linux**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Skip this step if `uv --version` already works. Voidscape also needs FFmpeg and FFprobe to inspect
images, video, or audio; `voidscape init` and `voidscape doctor` report whether they are ready. If
they are missing, use `winget install --id=Gyan.FFmpeg -e` on Windows, `brew install ffmpeg` on
macOS, or `sudo apt update && sudo apt install ffmpeg` on Debian/Ubuntu.

### 2. Install Voidscape and its agent skill

```powershell
uv tool install https://github.com/RikepilB/void-scape/archive/refs/heads/main.zip
uv tool update-shell
voidscape init
```

`uv tool install` creates the global `voidscape` command and installs `yt-dlp` in its isolated
environment. `voidscape init` copies the bundled skill to `~/.codex/skills/voidscape` and
`~/.agents/skills/voidscape`, checks local media tools, and does not approve a cloud job or model
download. If the command is not visible immediately after `uv tool update-shell`, open one new
terminal and run `voidscape init` there.

To use only the CLI, run `voidscape init --no-skill`. To update later, add `--upgrade` to the
`uv tool install` command, then run `voidscape init` again.

### 3. Optional: choose where your media and notes live

```powershell
# Preview Inbox, Library, and local transcription defaults.
voidscape customize

# Save only after reviewing the preview.
voidscape customize --yes --create-dirs
```

`customize` stores local paths and local defaults in `~/.voidscape/workspace.json`; it never stores
API keys. A model download and every cloud transcription job remain separate approvals.

### 4. Inspect, preview, then read

```powershell
voidscape doctor
voidscape route "https://www.reddit.com/r/videos/comments/..." --json
voidscape sources
voidscape inspect "meeting.mp4"
voidscape preview "meeting.mp4"
voidscape read "meeting.mp4" --workdir voidscape-output

# One local folder is one naturally ordered carousel.
voidscape inspect "slides"
voidscape preview "slides"
voidscape read "slides" --workdir slide-evidence
```

`inspect` is free source discovery. `preview` shows cost, dependencies, model-download state, and
whether audio would leave your machine. Video reads prepare `frames/`, `transcript.txt`, and
`manifest.json`; image reads prepare byte-preserving `images/` plus `manifest.json`. A carousel is
non-recursive, follows natural filename order, and is capped at 100 images. Cite video moments as
`[MM:SS]` and carousel evidence as `[image 1]`, never as fabricated timestamps.

Browser and phone control belong to the agent harness, not the media engine. With the approved
Chrome connection, Codex/ChatGPT or Claude can select permitted media in signed-in tabs, then run
Voidscape on the host that can access the files. ChatGPT Remote and Claude Code Remote Control can
continue that host task from a phone while the local tools remain on the host. Browser access does
not authenticate `yt-dlp`.

See [Multi-harness, browser, and remote support](docs/harness-support.md) and
[Public and authenticated sources](docs/authenticated-sources.md).

## Use it with an agent

After install, use `/voidscape <file-or-url>` in an agent harness that exposes skills as slash
commands, or simply ask the agent to inspect, preview, and read your media with Voidscape. The
agent should:

1. inspect the source;
2. preview the selected scope;
3. stop for explicit consent when cloud processing or a model download is required;
4. read the resulting artifacts and answer with `[MM:SS]` or `[image 1]` citations.

The installed skill teaches an agent the same `inspect → preview → read` flow. The concrete,
directly testable interface is `voidscape ...`; repository-only agent files under `.codex/agents/`
are development helpers, not installed slash commands.

Then give the evidence to your agent:

> Open `voidscape-output/manifest.json` and `transcript.txt`, then inspect `frames/`.
> Summarize the recording in three bullets. Support every factual claim with an exact `[MM:SS]`
> citation. If the evidence is insufficient, say so.

If an already-open agent session does not discover Voidscape after installation, start a new
session.

Repository contributors can still generate the copyright-free fixture with
`python scripts/create-demo-fixture.py` and exercise the source checkout directly; that development
path is not required for normal CLI use.

Testing with other people? Use the short, privacy-aware
[community prototype protocol](docs/community-testing.md) and its local
`survey-cli` questionnaire to capture task completion, consent clarity, timestamp usefulness, and
the exact points where testers need help.

## Choose the right path

| Need | Use | What happens |
| --- | --- | --- |
| Understand a local recording, demo, meeting, or screen capture | `inspect → preview → read` | Frames, transcript, and manifest stay local by default. |
| Read one image or a local carousel folder | `inspect → preview → read` | The non-recursive folder is naturally ordered, limited to 100 images, and copied locally without changing originals. |
| Read a voice memo or call | `read ... --tier audio` | The CLI prepares a local transcript; an agent can then author a note from that evidence. |
| Prepare an Instagram Reel URL | Repository helper (not installed) | `scripts/instagram_capture_helper.py` validates and deduplicates confirmed URLs; browser capture remains a user-observed development workflow. |
| Work from a signed-in saved collection | Browser selection, then `inspect -> preview -> read` on one permitted media URL | The user signs in and approves browser access; private collection automation is not shipped. |
| Run from an agent, hook, or schedule | `voidscape.py ... --json` or raw `video.py ... --envelope --compact` | Non-interactive commands; Voidscape does not ship a scheduler. |
| Read a public Substack article or RSS/Atom feed | `inspect -> preview -> read` | Article/feed reading is shipped; remote fetch requires explicit approval and public-network validation. |
| Route Reddit, LinkedIn, X, TikTok, or another web source | `voidscape route <url>` | Shows the default reader, safe override, capture status, and browser boundary without claiming universal compatibility. |

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

For video/audio, `read` creates `frames/`, `transcript.txt`, and `manifest.json`. For images, it
creates ordered `images/` and `manifest.json`; the agent cites `[image 1]`. When a workspace is
configured, the agent workflow can save its final answer as a Markdown note in your Library; the
engine itself does not pretend to author the note.

### What is the difference between `read` and `read-video`?

Voidscape is the guided name and product experience. `read-video` is the underlying, stable CLI and
legacy installed skill. Existing scripts keep using raw `video.py`; new users should start with
Voidscape.

### Can I automate it?

The CLI is non-interactive when given explicit flags, so it can be called by your own scripts or
agent hooks. Voidscape does not ship a scheduler or unattended worker. Any automation remains
responsible for preserving the cloud and model-download approval gates.

### What if a URL works in Chrome but not in the CLI?

Your browser may be signed in while the CLI is anonymous. Start with a public URL. For media your
account is permitted to access, export cookies for only that site, keep the file outside the repo,
and set `READ_VIDEO_YTDLP_COOKIES`. VPNs, expired sessions, platform extractor changes, and missing
Chrome site approval are separate common causes. See the
[authentication and troubleshooting guide](docs/authenticated-sources.md) and the
[browser/CLI test matrix](docs/chrome-use-case-matrix.md).

## Advanced engine interface

For scripts, subagents, and integrations, the raw engine remains stable:

```powershell
python skill/scripts/video.py manifest --compact
python skill/scripts/video.py probe "clip.mp4" --envelope --compact
python skill/scripts/video.py estimate "clip.mp4" --tier both --backend captions --envelope --compact
python skill/scripts/video.py run "clip.mp4" --tier both --backend captions --workdir out --envelope --compact

python skill/scripts/image.py manifest --compact
python skill/scripts/image.py probe "slides" --envelope --compact
python skill/scripts/image.py estimate "slides" --envelope --compact
python skill/scripts/image.py run "slides" --workdir slide-evidence --envelope --compact
```

The envelope is `{ok,data,error,meta}` with deterministic error codes and retryability metadata.
Run `voidscape sources --json` for the machine-readable platform matrix and use
`--reader video|article|image` only when an ambiguous source needs an explicit override.
See the [guided workflow and automation guide](docs/voidscape-guide.md),
[advanced CLI reference](docs/cli-reference.md), and [privacy/backend notes](skill/references/backends.md).

## Requirements

- Python 3.10+
- `ffmpeg` and `ffprobe` on `PATH`
- `yt-dlp` only for URLs
- `faster-whisper` only for local speech transcription

Run `voidscape doctor` to see what is ready without changing anything.

## Built with Codex

Voidscape began from Richard Pillaca's existing `read-video` engine; the import is explicitly
separated in [Build Week provenance](docs/BUILD_WEEK_PROVENANCE.md). Richard chose the product
problem and boundaries: local-first processing, `inspect → preview → read`, separate approval for
cloud transfer and model downloads, source-timeline citations, and deferring unattended
orchestration.

Codex accelerated the repository migration and audit, exposed mismatches between claims and the
installed package, reproduced the scoped-timestamp defect, wrote regression tests and fixes, and
hardened the judge install path. GPT-5.6 is the target agent model for reading the resulting frames
and transcript; the preview reports its vision-token estimate before that evidence is consumed.
The final submission should claim only work visible in dated post-import commits and the selected
Codex `/feedback` session.

See the [submission runbook](docs/build-week-submission.md) and
[project draft](docs/devpost-draft.md).

## License

[MIT](LICENSE) © Richard Pillaca.
