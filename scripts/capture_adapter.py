"""Shared capture-adapter contract, queue helpers, and CLI error emission.

Platform helpers (``instagram_capture_helper``, ``youtube_capture_helper``) keep
auth, selectors, and API access local while sharing the urls.md deduplication
and durable-append contract defined here.

Contract (inspect → preview → process):
- **inspect** — discover source queue/state; no mutation of urls.md or the
  platform account.
- **preview** — plan append/skip/completion actions; must not mutate urls.md
  or the platform account (``mutates_urls_md`` / ``mutates_source`` false).
- **process** — durable append to urls.md for new content keys, then mark
  completion on the platform (unsave, playlist delete, etc.); abort cleanly on
  partial failure after any durable write.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

ACTION_APPEND = "append"
ACTION_SKIP_DUPLICATE = "skip_duplicate"


class CaptureError(Exception):
    """Base error with a machine-readable ``error_type`` for CLI JSON output."""

    error_type = "capture_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


class CaptureAuthError(CaptureError):
    error_type = "authorization"


class CapturePartialWriteError(CaptureError):
    error_type = "partial_write"


class CaptureQuotaError(CaptureError):
    error_type = "quota"


class CaptureApiShapeError(CaptureError):
    error_type = "api_shape"


def is_duplicate(url: str, urls_md_path: Path) -> bool:
    """Return True when ``url`` already appears as a stripped line in urls.md."""
    if not urls_md_path.exists():
        return False
    lines = urls_md_path.read_text(encoding="utf-8").splitlines()
    return url in (line.strip() for line in lines)


def append_and_confirm(url: str, urls_md_path: Path) -> bool:
    """Append ``url`` to urls.md and confirm it is present after the write."""
    if not url or url != url.strip() or any(character in url for character in "\r\n\x00"):
        raise ValueError("queue entries must be nonempty single-line canonical URLs")
    urls_md_path.parent.mkdir(parents=True, exist_ok=True)
    with urls_md_path.open("a", encoding="utf-8") as f:
        f.write(url + "\n")
        f.flush()
        os.fsync(f.fileno())
    lines = urls_md_path.read_text(encoding="utf-8").splitlines()
    return url in (line.strip() for line in lines)


def preview_action_for_url(url: str, urls_md_path: Path) -> tuple[bool, str]:
    """Classify a single URL for preview: ``(duplicate, action)``."""
    duplicate = is_duplicate(url, urls_md_path)
    action = ACTION_SKIP_DUPLICATE if duplicate else ACTION_APPEND
    return duplicate, action


def confirm_existing_entry(url: str, urls_md_path: Path) -> bool:
    """Sync and revalidate duplicates, including entries left by a failed sync."""
    with urls_md_path.open("r+", encoding="utf-8") as stream:
        os.fsync(stream.fileno())
    return is_duplicate(url, urls_md_path)


def queue_append_result(url: str, urls_md_path: Path) -> dict[str, bool]:
    """Dedup-check and durable-append a single canonical URL.

    Returns ``{"duplicate": ..., "appended": ...}``. Does not mutate urls.md
    when the URL is already present.
    """
    duplicate = is_duplicate(url, urls_md_path)
    if duplicate:
        if not confirm_existing_entry(url, urls_md_path):
            raise CapturePartialWriteError("queued entry disappeared before confirmation")
        return {"duplicate": True, "appended": False}
    appended = append_and_confirm(url, urls_md_path)
    return {"duplicate": False, "appended": appended}


def durable_append_or_raise(
    url: str,
    urls_md_path: Path,
    *,
    partial_write_error: type[CapturePartialWriteError] | None = None,
    details: dict[str, Any] | None = None,
) -> bool:
    """Append durably or raise ``CapturePartialWriteError`` (or subclass)."""
    appended = append_and_confirm(url, urls_md_path)
    if not appended:
        exc_type = partial_write_error or CapturePartialWriteError
        raise exc_type(
            f"durable append failed for {url}",
            details=details or {"url": url},
        )
    return True


def emit_capture_error(err: Exception) -> int:
    """Print one JSON error object to stdout; return exit code 1."""
    if isinstance(err, CaptureError):
        payload: dict[str, Any] = {"error": str(err), "error_type": err.error_type}
        if err.details:
            payload["details"] = err.details
    else:
        payload = {"error": str(err), "error_type": "capture_error"}
    print(json.dumps(payload))
    return 1


@runtime_checkable
class CaptureAdapter(Protocol):
    """Minimal interface for platform capture helpers."""

    def inspect(self) -> dict[str, Any]:
        """Return source metadata without mutating urls.md or the platform account."""

    def preview(self, urls_md_path: Path) -> dict[str, Any]:
        """Plan capture actions without mutation."""

    def process(self, urls_md_path: Path) -> dict[str, Any]:
        """Durable append then platform completion marking; abort on partial failure."""
