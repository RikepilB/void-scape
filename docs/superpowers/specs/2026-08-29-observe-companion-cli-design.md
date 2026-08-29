# Thin observe companion CLI contract

**Date:** 2026-08-29
**Status:** Approved implementation contract
**Issue:** GitHub #23

## Goal

Add a small, on-demand capture surface that delegates to ffmpeg and optionally reports screenpipe
health. It produces a local screenshot or short silent clip; the user or agent then passes that file
through the existing `inspect -> preview -> read` workflow.

This is not an ambient recorder, browser controller, screenpipe reimplementation, or unattended
loop.

## Placement and public entry point

The implementation belongs at `skill/scripts/observe.py` as a focused sibling of `image.py`,
`article.py`, and `video.py`.

```text
python skill/scripts/observe.py doctor
python skill/scripts/observe.py screenshot --out <path.png>
python skill/scripts/observe.py clip --seconds <1-300> --out <path.mp4>
python skill/scripts/observe.py status --json
```

Do not add nested `voidscape.py observe ...` commands. `voidscape.py doctor` gains only an optional
observe-readiness section so users can discover the sibling tool. The installer already copies the
whole `skill/` tree and therefore includes `observe.py` without a new package mechanism.

## Shared command behavior

- Python standard library only; ffmpeg/ffprobe remain external executables.
- Human-readable output is the default.
- `--json` emits the standard `{ok,data,error,meta}` envelope as one JSON object.
- `--envelope` is an alias for `--json`; `--compact` removes pretty indentation.
- `meta.command` identifies the subcommand and `meta.protocol_version` is `1.0`.
- Output paths resolve to absolute paths in results.
- No command reads environment secrets, browser profiles, browser storage, or cookie files.
- Capture commands perform no network requests and capture no audio in v1.

The shared exit map stays aligned with the readers:

| Exit | Classification | Observe use |
| --- | --- | --- |
| 0 | success | command completed; optional screenpipe may still be unavailable |
| 1 | unexpected_error | unclassified internal exception |
| 2 | usage_error | argparse/flag error |
| 3 | input_error | invalid duration/path/extension or existing output |
| 4 | approval_required | reserved; not emitted by v1 capture |
| 5 | dependency_error | ffmpeg missing or platform/display unsupported |
| 6 | operation_failed | permission denial, timeout, ffmpeg failure, malformed local health response |

Error envelopes use `code`, `message`, `retryable`, and `exit_code`. Messages never include
screenpipe response bodies, environment dumps, command lines containing secrets, or browser state.

## Platform contract

| Platform | ffmpeg input | Status |
| --- | --- | --- |
| Windows | `gdigrab` with input `desktop` | Supported and personally testable on the project host |
| Linux X11 | `x11grab` with `$DISPLAY` or `--display` | Supported contract; CI uses mocks unless an X server exists |
| Linux Wayland | none selected | Unsupported in v1; report a dependency/platform error |
| macOS | none selected | Unsupported in v1; document honestly rather than guessing an AVFoundation device |

The capture is the full selected desktop/display. Window selection, crop regions, cursor policy,
multi-monitor enumeration, audio, and interactive pickers are non-goals for v1.

## `doctor`

### Inputs

```text
doctor [--screenpipe-url http://127.0.0.1:3030] [--json|--envelope] [--compact]
```

### Data

```json
{
  "platform": "windows",
  "capture_supported": true,
  "capture_backend": "gdigrab",
  "tools": {"ffmpeg": true, "ffprobe": true, "screenpipe": false},
  "display": "desktop",
  "screenpipe": {"reachable": false, "source": null}
}
```

`doctor` is read-only and returns exit 0 when optional screenpipe is absent. Missing ffmpeg or an
unsupported platform is reported in data; it becomes exit 5 only when a capture command is invoked.
The screenpipe URL must be loopback HTTP (`127.0.0.1`, `localhost`, or `::1`); reject remote hosts.

## `screenshot`

### Inputs

```text
screenshot --out <path.png> [--display <x11-display>] [--json|--envelope] [--compact]
```

### Validation

- `--out` is required and must end in `.png`.
- Parent directory must already exist and be a directory.
- Refuse an existing destination; no overwrite/force flag in v1.
- `--display` is valid only for Linux X11. Otherwise use `$DISPLAY`; missing display is exit 5.

### ffmpeg argv

Windows shape:

```text
ffmpeg -hide_banner -loglevel error -n -f gdigrab -framerate 1 -i desktop -frames:v 1 <out.png>
```

Linux X11 shape:

```text
ffmpeg -hide_banner -loglevel error -n -f x11grab -framerate 1 -i <display> -frames:v 1 <out.png>
```

Invoke with `subprocess.run(argv, shell=False)`. On success, verify the output exists and is non-empty.
Return its absolute path, media type `image`, byte count, backend, and platform.

## `clip`

### Inputs

```text
clip --seconds <integer> --out <path.mp4> [--display <x11-display>] [--json|--envelope] [--compact]
```

### Validation

- Duration is an integer from 1 through 300 seconds.
- `--out` must end in `.mp4`; parent exists; destination does not.
- Capture is silent: no microphone or system-audio device is opened.

### ffmpeg argv

Windows/Linux use their platform input from the screenshot contract, then:

```text
-framerate 15 -t <seconds> -c:v libx264 -preset ultrafast -pix_fmt yuv420p <out.mp4>
```

Use `-n`, `shell=False`, and a timeout of `seconds + 30`. On failure, remove only a partial file that
did not exist before this invocation. Return absolute path, media type `video`, requested duration,
byte count, backend, and platform.

## `status`

### Inputs

```text
status [--screenpipe-url http://127.0.0.1:3030] [--json|--envelope] [--compact]
```

### Resolution order

1. If a native `screenpipe` executable is on `PATH`, invoke `screenpipe status --json` with a short
   timeout and parse its JSON.
2. Otherwise query `<loopback-url>/health` with a two-second timeout using `urllib.request`.
3. Do not invoke `npx`, `bun`, installers, package registries, MCP, raw SQL, or databases.

Normalize only non-secret health fields when present:

```json
{
  "installed": true,
  "reachable": true,
  "source": "cli",
  "running": true,
  "health_status": "healthy",
  "frame_status": "healthy",
  "audio_status": "healthy",
  "last_capture": "<upstream value>",
  "last_audio_capture": "<upstream value>"
}
```

Absence/unreachability is an exit-0 status result because screenpipe is optional. A reachable but
malformed response is reported as `operation_failed` without echoing its body. Do not infer healthy
recording from a process, PID, port, or `running: true`; frame/audio status and freshness are separate.

This follows screenpipe's current skill semantics. Upstream is independently installed and moves
quickly, so field adapters must tolerate missing optional fields.

## Integration with `voidscape doctor`

`voidscape.py doctor` imports the observe module and adds:

```json
"observe": {
  "capture_supported": true,
  "backend": "gdigrab",
  "screenpipe_optional": true
}
```

Human output adds one `OK`, `MISSING`, or `UNSUPPORTED` observe line. Missing screenpipe never changes
the guided doctor's exit code. This integration performs no capture and does not start a service.

## Evidence handoff

Successful capture output is only a local source file:

```text
observe screenshot/clip -> local path
local path -> voidscape inspect -> preview -> read
evidence workdir -> agent answer with [image N] or [MM:SS]
```

`observe.py` never calls `voidscape.py read`, never adds `--allow-cloud` or
`--allow-model-download`, and never reuses an evidence workdir.

## Threat model

| Threat | Mitigation |
| --- | --- |
| OS recording without permission | Let ffmpeg/OS fail; return sanitized operation error; never bypass permission UI |
| Capturing too much | Explicit command, full-desktop disclosure, 300-second cap, no background loop |
| Overwriting user data | Existing output rejected; ffmpeg `-n`; no force flag |
| Partial output after failure | Delete only the new partial destination owned by this invocation |
| Command injection | Fixed argv list, `shell=False`, validated duration/extension/display |
| Localhost confused-deputy/SSRF | HTTP only; loopback host allowlist; fixed `/health`; two-second timeout |
| Health response leakage | Whitelist normalized status/freshness fields; never return raw body |
| Browser/profile leakage | No browser APIs, cookie files, storage paths, or credential discovery |
| Silent cloud or model work | Capture is local; later evidence read uses unchanged preview gates |
| Ambient retention | No service install/start, scheduler, database, or capture history in Voidscape |

## Test and verification contract

- Unit tests mock platform, `shutil.which`, subprocess, URL health, timeouts, and filesystem effects.
- Cover Windows argv and Linux-X11 argv without requiring live screen capture in CI.
- Cover missing ffmpeg/display, unsupported platform, invalid extension/duration, existing output,
  permission/ffmpeg failure, timeout, partial cleanup, optional screenpipe absent, malformed health,
  and loopback URL rejection.
- Assert no capture argv uses `shell=True` and no audio input is present.
- Update manifest/docs truth tests when #24 changes observe from `planned` to `shipped`.
- Run full pytest, compileall, isolated installer verification, and the key-free fixture through
  `inspect -> preview -> read` with a fresh workdir.

## Non-goals

- Always-on or scheduled recording
- Audio capture
- Browser automation or extension code
- screenpipe installation, service management, MCP, raw SQL, or database access
- macOS or Wayland capture claims
- Automatic evidence reading or approval forwarding
