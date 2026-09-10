"""Deterministic helper for the YouTube queue capture pipeline: OAuth-backed Data API
reads of a user-owned private queue playlist, content-keyed dedup against urls.md,
and playlist-item removal only after durable capture. No browser credentials — the
caller supplies an explicit OAuth access token obtained out of band."""
from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import urllib.error
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from capture_adapter import (
    confirm_existing_entry,
    CaptureError,
    append_and_confirm as append_and_confirm,
    durable_append_or_raise,
    emit_capture_error,
    is_duplicate as is_duplicate,
    preview_action_for_url,
)

API_BASE = "https://www.googleapis.com/youtube/v3"
DEFAULT_QUEUE_TITLE = "Read Video Queue"
_USER_AGENT = "voidscape-youtube-capture/1.0 (+python-urllib)"

_REQUIRED_DELETE_SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"
_READ_SCOPES = (
    "https://www.googleapis.com/auth/youtube.readonly",
    _REQUIRED_DELETE_SCOPE,
)

_DESIGN_PASS = {
    "api": "YouTube Data API v3",
    "source": "user-owned private queue playlist (Watch Later is API-inaccessible)",
    "oauth": {
        "consent": "explicit OAuth out of band; never read browser cookies or storage",
        "scopes_read": list(_READ_SCOPES),
        "scope_delete_required": _REQUIRED_DELETE_SCOPE,
        "note": "youtube.readonly is insufficient for playlistItems.delete",
    },
    "quota_units_per_call": {
        "playlists.list": 1,
        "playlistItems.list": 1,
        "playlistItems.delete": 50,
    },
    "rate_limits": "Google Cloud project daily quota (default 10,000 units/day); 429/403 quotaExceeded aborts",
    "terms": "Personal use via official API; comply with YouTube API Services Terms and Google API Services User Data Policy",
}


class YouTubeCaptureError(CaptureError):
    """YouTube-specific capture error; inherits shared CLI error_type contract."""


class YouTubeAuthError(YouTubeCaptureError):
    error_type = "authorization"


class YouTubeQuotaError(YouTubeCaptureError):
    error_type = "quota"


class YouTubeApiShapeError(YouTubeCaptureError):
    error_type = "api_shape"


class YouTubePartialWriteError(YouTubeCaptureError):
    error_type = "partial_write"


def canonical_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def _err_body(ex: urllib.error.HTTPError) -> str:
    try:
        raw = ex.read()
        return raw.decode("utf-8", errors="replace")[:500] if raw else ""
    except Exception:
        return ""


def _parse_api_error(status: int, body: str) -> YouTubeCaptureError:
    reason = ""
    message = body
    try:
        payload = json.loads(body)
        err = payload.get("error") if isinstance(payload, dict) else None
        err = err if isinstance(err, dict) else {}
        if isinstance(err.get("message"), str):
            message = err["message"] or message
        errors = err.get("errors")
        for item in errors if isinstance(errors, list) else []:
            if isinstance(item, dict) and isinstance(item.get("reason"), str) and item["reason"]:
                reason = item["reason"]
                break
    except json.JSONDecodeError:
        pass

    if status in (401, 403) and reason in {
        "quotaExceeded",
        "dailyLimitExceeded",
        "userRateLimitExceeded",
    }:
        return YouTubeQuotaError(message or f"HTTP {status}", details={"reason": reason, "body": body})
    if status in (401, 403):
        return YouTubeAuthError(message or f"HTTP {status}", details={"reason": reason, "body": body})
    return YouTubeCaptureError(message or f"HTTP {status}", details={"reason": reason, "body": body})


class YouTubeClient:
    def __init__(
        self,
        access_token: str,
        *,
        urlopen_fn: Callable[..., Any] | None = None,
        ssl_context: ssl.SSLContext | None = None,
    ) -> None:
        self.access_token = access_token
        self._urlopen = urlopen_fn or urlopen
        self._ssl_context = ssl_context or ssl.create_default_context()

    def _request(self, method: str, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        query = f"?{urlencode(params)}" if params else ""
        url = f"{API_BASE}/{path}{query}"
        req = Request(
            url,
            method=method,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json",
                "User-Agent": _USER_AGENT,
            },
        )
        try:
            with self._urlopen(req, timeout=60, context=self._ssl_context) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as ex:
            raise _parse_api_error(ex.code, _err_body(ex) or str(ex)) from ex
        except urllib.error.URLError as ex:
            raise YouTubeCaptureError(f"network error: {ex}") from ex

        if not raw and method == "DELETE":
            return {}
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as ex:
            raise YouTubeApiShapeError("response was not valid JSON", details={"body": raw}) from ex
        if not isinstance(data, dict):
            raise YouTubeApiShapeError("top-level response is not an object", details={"body": raw})
        return data

    def find_playlist_by_title(self, title: str) -> dict[str, Any]:
        page_token = ""
        seen_tokens: set[str] = set()
        while True:
            params = {"part": "snippet", "mine": "true", "maxResults": "50"}
            if page_token:
                params["pageToken"] = page_token
            data = self._request("GET", "playlists", params)
            page_items, next_token = _playlist_page(data)
            for item in page_items:
                snippet = _object_field(item, "snippet")
                if snippet.get("title") == title:
                    playlist_id = item.get("id")
                    if not isinstance(playlist_id, str) or not playlist_id:
                        raise YouTubeApiShapeError("playlist match missing id", details={"item": item})
                    return {
                        "playlist_id": playlist_id,
                        "title": snippet.get("title") or title,
                    }
            page_token = _next_token(next_token, seen_tokens)
            if not page_token:
                break
        raise YouTubeCaptureError(
            f"no owned playlist titled {title!r}; create one or pass --playlist-id",
            details={"title": title},
        )

    def list_playlist_items(self, playlist_id: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page_token = ""
        seen_tokens: set[str] = set()
        while True:
            params = {
                "part": "snippet,contentDetails",
                "playlistId": playlist_id,
                "maxResults": "50",
            }
            if page_token:
                params["pageToken"] = page_token
            data = self._request("GET", "playlistItems", params)
            page_items, next_token = _playlist_page(data)
            for raw in page_items:
                parsed = _parse_playlist_item(raw)
                if parsed is not None:
                    items.append(parsed)
            page_token = _next_token(next_token, seen_tokens)
            if not page_token:
                break
        return items

    def delete_playlist_item(self, playlist_item_id: str) -> None:
        self._request("DELETE", "playlistItems", {"id": playlist_item_id})


def _playlist_page(data: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    items = data.get("items")
    items = [] if items is None else items
    token = data.get("nextPageToken")
    token = "" if token is None else token
    if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
        raise YouTubeApiShapeError("playlist items must be a list of objects")
    if not isinstance(token, str):
        raise YouTubeApiShapeError("next page token must be a string")
    return items, token


def _next_token(token: str, seen: set[str]) -> str:
    if token:
        if token in seen:
            raise YouTubeApiShapeError("playlist pagination repeated a page token")
        seen.add(token)
    return token


def _object_field(item: dict[str, Any], name: str) -> dict[str, Any]:
    value = item.get(name)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise YouTubeApiShapeError(f"playlist {name} must be an object")
    return value


def _parse_playlist_item(raw: dict[str, Any]) -> dict[str, Any] | None:
    playlist_item_id = raw.get("id")
    snippet = _object_field(raw, "snippet")
    content = _object_field(raw, "contentDetails")
    resource = _object_field(snippet, "resourceId")
    video_id = resource.get("videoId") or content.get("videoId")
    if not playlist_item_id or not video_id:
        return None
    if not isinstance(playlist_item_id, str) or not isinstance(video_id, str):
        raise YouTubeApiShapeError("playlist item and video IDs must be strings")
    return {
        "playlist_item_id": playlist_item_id,
        "video_id": video_id,
        "title": snippet.get("title") or "",
        "url": canonical_url(video_id),
    }


def resolve_playlist_id(
    client: YouTubeClient,
    *,
    playlist_id: str | None,
    playlist_title: str | None,
) -> tuple[str, str | None]:
    if playlist_id:
        return playlist_id, None
    title = playlist_title or DEFAULT_QUEUE_TITLE
    found = client.find_playlist_by_title(title)
    return found["playlist_id"], found.get("title")


def inspect_queue(
    client: YouTubeClient,
    *,
    playlist_id: str | None = None,
    playlist_title: str | None = None,
) -> dict[str, Any]:
    resolved_id, resolved_title = resolve_playlist_id(
        client, playlist_id=playlist_id, playlist_title=playlist_title
    )
    items = client.list_playlist_items(resolved_id)
    return {
        "design": _DESIGN_PASS,
        "playlist_id": resolved_id,
        "playlist_title": resolved_title,
        "item_count": len(items),
        "items": items,
    }


def preview_capture(
    client: YouTubeClient,
    urls_md_path: Path,
    *,
    playlist_id: str | None = None,
    playlist_title: str | None = None,
) -> dict[str, Any]:
    resolved_id, resolved_title = resolve_playlist_id(
        client, playlist_id=playlist_id, playlist_title=playlist_title
    )
    items = client.list_playlist_items(resolved_id)
    planned: list[dict[str, Any]] = []
    to_append = 0
    duplicates = 0
    for item in items:
        duplicate, action = preview_action_for_url(item["url"], urls_md_path)
        if duplicate:
            duplicates += 1
        else:
            to_append += 1
        planned.append(
            {
                **item,
                "duplicate": duplicate,
                "action": action,
                "safe_to_remove": True,
            }
        )
    return {
        "playlist_id": resolved_id,
        "playlist_title": resolved_title,
        "items": planned,
        "summary": {
            "total": len(planned),
            "to_append": to_append,
            "duplicates": duplicates,
        },
        "mutates_playlist": False,
        "mutates_urls_md": False,
    }


def process_capture(
    client: YouTubeClient,
    urls_md_path: Path,
    *,
    playlist_id: str | None = None,
    playlist_title: str | None = None,
) -> dict[str, Any]:
    preview = preview_capture(
        client,
        urls_md_path,
        playlist_id=playlist_id,
        playlist_title=playlist_title,
    )
    processed: list[dict[str, Any]] = []
    for item in preview["items"]:
        url = item["url"]
        duplicate = item["duplicate"]
        appended = False
        if duplicate:
            if not confirm_existing_entry(url, urls_md_path):
                raise YouTubePartialWriteError("queued entry disappeared before confirmation")
        else:
            appended = durable_append_or_raise(
                url,
                urls_md_path,
                partial_write_error=YouTubePartialWriteError,
                details={"item": item, "processed": processed},
            )
        try:
            client.delete_playlist_item(item["playlist_item_id"])
        except YouTubeCaptureError as ex:
            raise YouTubePartialWriteError(
                f"playlist item delete failed after capture for {url}: {ex}",
                details={
                    "item": item,
                    "appended": appended,
                    "duplicate": duplicate,
                    "processed": processed,
                    "underlying": str(ex),
                },
            ) from ex
        processed.append(
            {
                "playlist_item_id": item["playlist_item_id"],
                "video_id": item["video_id"],
                "url": url,
                "duplicate": duplicate,
                "appended": appended,
                "removed_from_playlist": True,
            }
        )
    return {
        "playlist_id": preview["playlist_id"],
        "playlist_title": preview.get("playlist_title"),
        "processed": processed,
        "summary": {
            "total": len(processed),
            "appended": sum(1 for p in processed if p["appended"]),
            "duplicates": sum(1 for p in processed if p["duplicate"]),
            "removed_from_playlist": len(processed),
        },
        "aborted": False,
    }


def _access_token_from_args(args: argparse.Namespace) -> str:
    token = getattr(args, "access_token", None) or os.environ.get("YOUTUBE_ACCESS_TOKEN", "")
    if not token:
        raise YouTubeAuthError(
            "missing OAuth access token; pass --access-token or set YOUTUBE_ACCESS_TOKEN",
        )
    return token


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="youtube_capture_helper")
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--access-token",
        help="OAuth access token from an explicit consent flow (or set YOUTUBE_ACCESS_TOKEN)",
    )
    playlist = common.add_mutually_exclusive_group()
    playlist.add_argument("--playlist-id", help="YouTube playlist ID for the queue")
    playlist.add_argument(
        "--playlist-title",
        default=None,
        help=f"Discover an owned playlist by title (default: {DEFAULT_QUEUE_TITLE!r})",
    )

    sub.add_parser("inspect", parents=[common], help="list queue items and design metadata")
    p_preview = sub.add_parser(
        "preview",
        parents=[common],
        help="show planned append/remove actions without mutating anything",
    )
    p_preview.add_argument("urls_md_path")

    p_process = sub.add_parser(
        "process",
        parents=[common],
        help="append new URLs durably, then remove captured playlist items",
    )
    p_process.add_argument("urls_md_path")

    args = parser.parse_args(argv)

    try:
        token = _access_token_from_args(args)
        client = YouTubeClient(token)
        playlist_id = args.playlist_id
        playlist_title = args.playlist_title
        if args.command == "inspect":
            result = inspect_queue(
                client,
                playlist_id=playlist_id,
                playlist_title=playlist_title if not playlist_id else None,
            )
        elif args.command == "preview":
            result = preview_capture(
                client,
                Path(args.urls_md_path),
                playlist_id=playlist_id,
                playlist_title=playlist_title if not playlist_id else None,
            )
        elif args.command == "process":
            result = process_capture(
                client,
                Path(args.urls_md_path),
                playlist_id=playlist_id,
                playlist_title=playlist_title if not playlist_id else None,
            )
        else:
            return 1
    except (YouTubeCaptureError, ValueError) as err:
        return emit_capture_error(err)

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
