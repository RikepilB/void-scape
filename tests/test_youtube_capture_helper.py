"""Tests for the YouTube capture helper — mocked API only, no live network."""
from __future__ import annotations

import io
import json
import subprocess
import sys
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from youtube_capture_helper import (
    YouTubeApiShapeError,
    YouTubeAuthError,
    YouTubeClient,
    YouTubePartialWriteError,
    YouTubeQuotaError,
    append_and_confirm,
    canonical_url,
    inspect_queue,
    is_duplicate,
    preview_capture,
    process_capture,
)

REPO = Path(__file__).resolve().parent.parent
HELPER_SCRIPT = REPO / "scripts" / "youtube_capture_helper.py"

PLAYLIST_ID = "PLqueue123"
ITEM_ONE = {
    "id": "PLIitem001",
    "snippet": {
        "title": "First video",
        "resourceId": {"kind": "youtube#video", "videoId": "vid001abc"},
    },
    "contentDetails": {"videoId": "vid001abc"},
}
ITEM_TWO = {
    "id": "PLIitem002",
    "snippet": {
        "title": "Second video",
        "resourceId": {"kind": "youtube#video", "videoId": "vid002def"},
    },
    "contentDetails": {"videoId": "vid002def"},
}


def _response(payload: dict, *, status: int = 200) -> MagicMock:
    body = json.dumps(payload).encode("utf-8")
    resp = MagicMock()
    resp.read.return_value = body
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    resp.status = status
    return resp


def _client_with_responses(responses: list) -> YouTubeClient:
    call_idx = {"i": 0}

    def fake_urlopen(req, timeout=60, context=None):
        idx = call_idx["i"]
        call_idx["i"] += 1
        if idx >= len(responses):
            raise AssertionError(f"unexpected extra request #{idx + 1}: {req.full_url}")
        item = responses[idx]
        if isinstance(item, Exception):
            raise item
        return _response(item)

    return YouTubeClient("test-token", urlopen_fn=fake_urlopen)


def test_canonical_url():
    assert canonical_url("vid001abc") == "https://www.youtube.com/watch?v=vid001abc"


def test_is_duplicate_and_append(tmp_path):
    urls_md = tmp_path / "urls.md"
    url = canonical_url("vid001abc")
    assert is_duplicate(url, urls_md) is False
    assert append_and_confirm(url, urls_md) is True
    assert is_duplicate(url, urls_md) is True


def test_inspect_lists_items_with_design_metadata():
    client = _client_with_responses(
        [{"items": [ITEM_ONE, ITEM_TWO], "pageInfo": {"totalResults": 2}}]
    )
    result = inspect_queue(client, playlist_id=PLAYLIST_ID)
    assert result["playlist_id"] == PLAYLIST_ID
    assert result["item_count"] == 2
    assert result["items"][0]["video_id"] == "vid001abc"
    assert "design" in result
    assert result["design"]["api"] == "YouTube Data API v3"
    assert any("youtube.readonly" in scope for scope in result["design"]["oauth"]["scopes_read"])


def test_preview_marks_duplicates_without_mutation(tmp_path):
    urls_md = tmp_path / "urls.md"
    urls_md.write_text(canonical_url("vid001abc") + "\n", encoding="utf-8")
    client = _client_with_responses(
        [{"items": [ITEM_ONE, ITEM_TWO], "pageInfo": {"totalResults": 2}}]
    )
    result = preview_capture(client, urls_md, playlist_id=PLAYLIST_ID)
    assert result["summary"] == {"total": 2, "to_append": 1, "duplicates": 1}
    assert result["items"][0]["action"] == "skip_duplicate"
    assert result["items"][1]["action"] == "append"
    assert result["mutates_playlist"] is False
    assert urls_md.read_text(encoding="utf-8").count("\n") == 1


def test_process_appends_then_deletes_in_order(tmp_path):
    urls_md = tmp_path / "urls.md"
    client = _client_with_responses(
        [
            {"items": [ITEM_ONE, ITEM_TWO], "pageInfo": {"totalResults": 2}},
            {},
            {},
        ]
    )
    result = process_capture(client, urls_md, playlist_id=PLAYLIST_ID)
    assert result["summary"]["appended"] == 2
    assert result["summary"]["removed_from_playlist"] == 2
    lines = urls_md.read_text(encoding="utf-8").splitlines()
    assert lines == [canonical_url("vid001abc"), canonical_url("vid002def")]


def test_process_skips_append_for_duplicate_but_still_deletes(tmp_path):
    urls_md = tmp_path / "urls.md"
    urls_md.write_text(canonical_url("vid001abc") + "\n", encoding="utf-8")
    client = _client_with_responses(
        [
            {"items": [ITEM_ONE], "pageInfo": {"totalResults": 1}},
            {},
        ]
    )
    result = process_capture(client, urls_md, playlist_id=PLAYLIST_ID)
    assert result["processed"][0]["duplicate"] is True
    assert result["processed"][0]["appended"] is False
    assert result["processed"][0]["removed_from_playlist"] is True
    assert urls_md.read_text(encoding="utf-8").strip() == canonical_url("vid001abc")


def test_process_aborts_on_delete_failure_after_append(tmp_path, monkeypatch):
    urls_md = tmp_path / "urls.md"

    def fail_delete(self, playlist_item_id: str) -> None:
        raise YouTubeAuthError("forbidden delete", details={"reason": "forbidden"})

    monkeypatch.setattr(YouTubeClient, "delete_playlist_item", fail_delete)
    client = _client_with_responses(
        [{"items": [ITEM_ONE], "pageInfo": {"totalResults": 1}}]
    )
    with pytest.raises(YouTubePartialWriteError) as exc:
        process_capture(client, urls_md, playlist_id=PLAYLIST_ID)
    assert canonical_url("vid001abc") in urls_md.read_text(encoding="utf-8")
    assert exc.value.error_type == "partial_write"


def test_client_maps_quota_errors():
    body = json.dumps(
        {
            "error": {
                "message": "quota exceeded",
                "errors": [{"reason": "quotaExceeded"}],
            }
        }
    )
    err = urllib.error.HTTPError("url", 403, "Forbidden", hdrs=None, fp=io.BytesIO(body.encode()))
    client = _client_with_responses([err])
    with pytest.raises(YouTubeQuotaError):
        client.list_playlist_items(PLAYLIST_ID)


def test_client_maps_auth_errors():
    body = json.dumps(
        {
            "error": {
                "message": "invalid token",
                "errors": [{"reason": "authError"}],
            }
        }
    )
    err = urllib.error.HTTPError("url", 401, "Unauthorized", hdrs=None, fp=io.BytesIO(body.encode()))
    client = _client_with_responses([err])
    with pytest.raises(YouTubeAuthError):
        client.list_playlist_items(PLAYLIST_ID)


def test_client_rejects_invalid_json():
    def fake_urlopen(req, timeout=60, context=None):
        resp = MagicMock()
        resp.read.return_value = b"not-json"
        resp.__enter__.return_value = resp
        resp.__exit__.return_value = False
        return resp

    client = YouTubeClient("test-token", urlopen_fn=fake_urlopen)
    with pytest.raises(YouTubeApiShapeError):
        client.list_playlist_items(PLAYLIST_ID)


def test_find_playlist_by_title():
    client = _client_with_responses(
        [
            {
                "items": [
                    {"id": "PLother", "snippet": {"title": "Other"}},
                    {"id": PLAYLIST_ID, "snippet": {"title": "Read Video Queue"}},
                ]
            }
        ]
    )
    found = client.find_playlist_by_title("Read Video Queue")
    assert found == {"playlist_id": PLAYLIST_ID, "title": "Read Video Queue"}


def test_cli_preview_requires_token(tmp_path):
    urls_md = tmp_path / "urls.md"
    result = subprocess.run(
        [
            sys.executable,
            str(HELPER_SCRIPT),
            "preview",
            "--playlist-id",
            PLAYLIST_ID,
            str(urls_md),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["error_type"] == "authorization"
