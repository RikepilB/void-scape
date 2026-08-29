# Observe and capture with Voidscape

This playbook composes a browser-capable harness, optional capture tooling, and Voidscape without
turning Voidscape into a browser controller or ambient recorder.

**Status:** `shipped` documentation; observe CLI `planned`

[Back to agent docs](index.md) · Canonical sources: [harness support](../harness-support.md),
[browser/CLI matrix](../chrome-use-case-matrix.md), and
[authenticated sources](../authenticated-sources.md)

## Responsibility boundary

```text
user-approved harness -> browse, click, screenshot, or save a recording
optional capture tool -> produce a chosen local image or clip
Voidscape -> inspect -> preview -> read -> manifest + citable evidence
```

The harness owns live interaction. The operating system owns screen-recording permission. An
optional companion owns capture history. Voidscape starts with a URL or local file and keeps its
normal per-job cloud and model-download gates.

Voidscape never reads browser credentials, cookies, storage, or secrets. It never exports browser
state. Browser site approval does not authorize CLI authentication, cloud spend, or model downloads.

## One-time setup

### Codex or ChatGPT

1. Follow the official [Codex Chrome extension](https://developers.openai.com/codex/chrome-extension/)
   setup and grant only the sites needed for the task.
2. Use the harness's current permission UI to retain site access only where appropriate. Permission
   persistence and scope are controlled by the harness/browser, not Voidscape.
3. For mobile continuation, follow [Codex remote connections](https://developers.openai.com/codex/remote-connections/).
   The paired host must remain available and must be able to reach the local files and CLI.

### Claude

1. Follow [Claude Code with Chrome](https://docs.anthropic.com/en/docs/claude-code/chrome) and grant
   the required site access in Claude/Chrome.
2. Follow [Claude Code Remote Control](https://docs.anthropic.com/en/docs/claude-code/remote-control)
   when continuing the running local session from another device.
3. Treat the complete Claude-to-Voidscape composition as `unverified` until reproduced on the
   target host; vendor documentation establishes the harness features, not this integration.

### Host capture folder and permissions

1. Choose a dedicated local folder for task captures and keep private material out of the repo.
2. Grant OS screen-recording permission only to the harness or capture tool that needs it.
3. Test one harmless screenshot before a real task.
4. Use a new empty Voidscape evidence workdir for each read.

Pre-approving a narrow domain list can reduce repeated harness prompts. It does not promise zero
prompts: new sites, sensitive actions, OS recording, cloud transfer, and model downloads remain
separate decisions.

## Recipe 1 — browser task to screenshot or short clip

1. In a permitted tab, ask the harness to complete the browsing task.
2. Ask the harness or an independently installed capture tool to save a screenshot or short clip to
   the known local capture folder. Confirm the final path.
3. For a screenshot:

   ```powershell
   python skill/scripts/voidscape.py inspect "C:\path\capture.png"
   python skill/scripts/voidscape.py preview "C:\path\capture.png"
   python skill/scripts/voidscape.py read "C:\path\capture.png" --workdir "C:\path\evidence-image"
   ```

4. For a clip:

   ```powershell
   python skill/scripts/voidscape.py inspect "C:\path\capture.mp4"
   python skill/scripts/voidscape.py preview "C:\path\capture.mp4" --tier both
   python skill/scripts/voidscape.py read "C:\path\capture.mp4" --tier both --workdir "C:\path\evidence-clip"
   ```

5. Stop for any previewed approval. Read the resulting bundle with `[image N]` or `[MM:SS]`
   citations.

Voidscape does not currently ship the capture command; issue #24 owns the optional thin wrapper.

## Recipe 2 — public video URL without browser cookies

Copy the public URL from a permitted page and pass it directly to the guided CLI:

```powershell
python skill/scripts/voidscape.py inspect "https://example.com/public-video"
python skill/scripts/voidscape.py preview "https://example.com/public-video" --tier both
python skill/scripts/voidscape.py read "https://example.com/public-video" --tier both --workdir evidence-public
```

Start anonymously. A page being visible in Chrome does not prove the media endpoint is public. If
the CLI returns an authentication/platform error, surface it rather than trying to extract browser
state.

## Recipe 3 — account-scoped media with an explicit cookie file

Use this only for media the user is permitted to access.

1. The user separately creates a site-scoped Netscape `cookies.txt` outside the repository.
2. The user sets `READ_VIDEO_YTDLP_COOKIES` to that file path on the host.
3. Run `inspect` again and follow the normal preview and approval gates.
4. Delete or rotate the exported file according to the user's security practice.

The harness never exports the file, reads its contents, or copies it into Voidscape. Voidscape does
not discover browser profiles or storage; it passes only the user-configured file path to the media
tool. Never print the file or include it in evidence.

## Optional screenpipe companion

screenpipe is a separately installed, source-available desktop-memory product. It is not a
Voidscape dependency and is not started or configured by the Voidscape installer.

Current upstream examples use:

```text
npx screenpipe record
npx screenpipe setup
claude mcp add screenpipe -- npx -y screenpipe-mcp@latest
```

The issue brief's older `screenpipe service install` spelling is not present in the current upstream
README. Follow the [current screenpipe documentation](https://docs.screenpi.pe) and pin a release
when reproducibility matters; upstream warns that `main` moves quickly.

screenpipe currently documents a localhost REST API (default port 3030), MCP access, local screen
history, and a video-export pipe. A user or harness may query recent permitted frames and export a
chosen clip, then pass that local file to Voidscape. Voidscape does not query screenpipe on its own.

Keep the service bound locally, apply screenpipe's current authentication and permission guidance,
and never treat localhost as a sufficient trust boundary. Ambient retention, excluded apps, audio
capture, cloud features, and deletion remain screenpipe/user responsibilities.

## Permission boundary

| Decision | Owner | Reuse across jobs? |
| --- | --- | --- |
| Browser site/tab permission | User + harness | According to current harness/browser scope |
| Browser navigation/click/type | Harness within granted scope | Task/session-specific |
| OS screen/audio recording | User + operating system | According to OS permission state |
| screenpipe capture and retention | User + screenpipe | According to separate screenpipe config |
| CLI account cookie file | User | Until explicitly removed/rotated; never discovered by harness |
| Cloud transcription | User + Voidscape preview | No; approve the current job |
| Local model download | User + Voidscape preview | Approve acquisition separately |
| Evidence reading cost | Agent/harness billing context | Preview again when scope/model changes |

## Failure handling

- Host unavailable: reconnect the paired host; do not reroute silently to cloud execution.
- Capture path missing: confirm the actual local file before `inspect`.
- OS recording denied: report the missing permission; do not loop or install tools automatically.
- URL works in browser but not CLI: treat browser and CLI authentication as separate.
- screenpipe API/MCP unavailable: continue with a manual/harness capture or skip; screenpipe is
  optional.
- Preview requires approval: stop and present that specific decision.

## Pattern sources

- [screenpipe](https://github.com/screenpipe/screenpipe): optional local capture/history, freshness,
  API, and export patterns.
- [automated_browser `devel`](https://github.com/deaspo/automated_browser/tree/devel): structured
  action and session-replay patterns only.

Voidscape does not adopt always-on recording as its core, an autonomous LLM browser loop, raw page
uploads to a model, cookie scraping, or unattended action replay.
