# Capture adapters

Capture adapters move bookmarked/saved media from a platform into Voidscape's
`urls.md` queue. Each platform ships a helper script under `scripts/` that
implements the shared contract in `scripts/capture_adapter.py`.

## Shared vs platform-specific

| Concern | Shared (`capture_adapter.py`) | Platform-specific |
|---|---|---|
| Content-key dedup | Strip-match against `urls.md` lines | Canonical URL / ID extraction |
| Queue write | `append_and_confirm` with parent-dir creation | — |
| Preview classification | `preview_action_for_url` → `append` / `skip_duplicate` | Item discovery (API list, browser scrape) |
| Process ordering | Append (or skip duplicate) **before** completion marking | Completion action (unsave reel, delete playlist item) |
| Clean abort | `CapturePartialWriteError` after durable write fails or completion fails | Error mapping (quota, auth, selector break) |
| Auth / consent | Never read browser cookies or storage | OAuth token (YouTube), Codex Chrome control (Instagram browser subagent) |
| Inspect / preview / process CLI | JSON shape per platform; shared semantics | Command surface, design metadata |

### Instagram (`instagram_capture_helper.py`)

- **Inspect / preview** live in the Codex Chrome browser subagent; the helper
  only implements the queue-write half for one reel at a time.
- **Platform-specific:** shortcode extraction, reel canonical URL, host allowlist.
- **Completion marking:** `safe_to_unsave` — true when the URL is already in
  the vault or was durably appended (browser unsave is a separate approved step).

### YouTube (`youtube_capture_helper.py`)

- **Inspect / preview / process** are fully implemented in the helper via
  YouTube Data API v3 and an explicit OAuth access token.
- **Platform-specific:** playlist discovery, `playlistItems.list` / `.delete`,
  quota/auth error mapping, design-pass metadata in `inspect`.
- **Completion marking:** `removed_from_playlist` after durable append (or
  confirmed duplicate); delete aborts with `partial_write` if append succeeded
  but removal failed.

### Instagram follow audit (`ig_follow_audit_helper.py`)

- **Inspect / preview / process** are fully local: the user exports both lists
  (Instagram data-download JSON or one-handle-per-line text) and the helper
  diffs them into a citable report. No network, no browser, no account access.
- **Read-only by contract:** it never unfollows, follows, or messages; the
  suggested review list is acted on by the human. See
  [`agents/capture-adapters/ig-follow-audit.md`](agents/capture-adapters/ig-follow-audit.md).

## Contract

1. **Inspect** — read source state only; no `urls.md` or account mutation.
2. **Preview** — show planned per-item actions; set `mutates_urls_md` /
   `mutates_playlist` (or equivalent) to `false`.
3. **Process** — for each item: canonicalize content key → dedup against
   `urls.md` → durable append when new → mark complete on platform → on any
   failure after a durable append, abort and surface `partial_write` with context.
4. **Approval** — account mutation (unsave, playlist delete) never runs inside
   preview; callers must obtain explicit user consent before `process`.

## Adding a platform (concrete example)

Suppose you add a "saved posts" capture for ExampleSocial:

```python
# scripts/examplesocial_capture_helper.py
from pathlib import Path
from capture_adapter import (
    ACTION_APPEND,
    ACTION_SKIP_DUPLICATE,
    CapturePartialWriteError,
    append_and_confirm,
    emit_capture_error,
    is_duplicate,
    preview_action_for_url,
)

def canonical_url(post_id: str) -> str:
    return f"https://examplesocial.com/p/{post_id}"

def preview_saved(client, urls_md_path: Path) -> dict:
    items = client.list_saved_posts()  # platform API or browser scrape
    planned = []
    for item in items:
        url = canonical_url(item["id"])
        duplicate, action = preview_action_for_url(url, urls_md_path)
        planned.append({**item, "url": url, "duplicate": duplicate, "action": action})
    return {
        "items": planned,
        "mutates_urls_md": False,
        "mutates_saved_collection": False,
    }

def process_saved(client, urls_md_path: Path) -> dict:
    preview = preview_saved(client, urls_md_path)
    processed = []
    for item in preview["items"]:
        url = item["url"]
        if item["duplicate"]:
            appended = False
        else:
            appended = append_and_confirm(url, urls_md_path)
            if not appended:
                raise CapturePartialWriteError(
                    f"durable append failed for {url}",
                    details={"item": item, "processed": processed},
                )
        try:
            client.remove_saved(item["id"])  # only after durable capture
        except Exception as ex:
            raise CapturePartialWriteError(
                f"saved-post removal failed after capture for {url}: {ex}",
                details={"item": item, "appended": appended, "processed": processed},
            ) from ex
        processed.append({"url": url, "duplicate": item["duplicate"], "appended": appended})
    return {"processed": processed, "aborted": False}
```

Wire a CLI that mirrors YouTube's `inspect` / `preview` / `process` commands,
keep OAuth or browser selectors inside the platform module, and add adapter
tests under `tests/test_examplesocial_capture_helper.py` plus contract coverage
via `tests/test_capture_adapter.py`.

See also [`docs/youtube-queue-capture.md`](youtube-queue-capture.md) for a
production adapter walkthrough.
