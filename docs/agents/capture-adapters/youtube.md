# YouTube capture adapter

The YouTube repository adapter reads a user-owned private playlist through the official YouTube Data
API, appends canonical URLs durably, then removes captured playlist items.

**Status:** `dev-only`

[Back to agent docs](../index.md) · Canonical sources:
[`youtube_capture_helper.py`](../../../scripts/youtube_capture_helper.py) and
[YouTube queue capture](../../youtube-queue-capture.md)

## Status board

| Capability | Status | Boundary |
| --- | --- | --- |
| Inspect a configured private queue playlist | `dev-only` | Repository script, explicit OAuth token |
| Preview append/delete actions | `dev-only` | Dry run; no playlist mutation |
| Append URL, then delete playlist item | `dev-only` | Mutation occurs only after durable queue write |
| Read an individual supported YouTube URL | `shipped` | Video reader, separate consent-gated job |
| Installed queue-capture command | `planned` | Not included by the skill installer |
| Watch Later API queue | `parked` | Official API does not expose the required operations |

## Commands

```powershell
python scripts/youtube_capture_helper.py inspect ...
python scripts/youtube_capture_helper.py preview ...
python scripts/youtube_capture_helper.py process ...
```

Use `--help` and the canonical setup guide for token, playlist, and queue arguments. Do not place
OAuth tokens in the repository or documentation. The adapter uses the YouTube Data API v3; it does
not automate the website or read browser cookies.

`process` preserves append-before-delete ordering. If the queue write fails, the playlist item must
remain. Each captured URL later enters Voidscape's separate `inspect -> preview -> read` flow.
