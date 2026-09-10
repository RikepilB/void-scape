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
import youtube_capture_helper as youtube

from youtube_capture_helper import (
    YouTubeApiShapeError,
    YouTubeAuthError,
    YouTubeClient,
    YouTubePartialWriteError,
    YouTubeQuotaError,
    _parse_api_error,
    append_and_confirm,
    canonical_url,
    inspect_queue,
    is_duplicate,
    preview_capture,
    process_capture,
)

REPO = Path(__file__).resolve().parent.parent
HELPER_SCRIPT = REPO / "scripts" / "youtube_capture_helper.py"


@pytest.mark.parametrize("payload", [None, [], 1, "error", {"error": None},
    {"error": []}, {"error": {"message": [], "errors": 1}},
    {"error": {"errors": [None, 1, [], {"reason": []}]}}])
def test_unexpected_api_error_shape_preserves_http_classification(payload):
    error = _parse_api_error(403, json.dumps(payload))
    assert isinstance(error, YouTubeAuthError)
    assert error.details["reason"] == ""


def test_api_error_skips_malformed_reasons_before_quota():
    error = _parse_api_error(403, json.dumps({"error": {"errors": [
        None, {"reason": []}, {"reason": "quotaExceeded"}]}}))
    assert isinstance(error, YouTubeQuotaError)

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


@pytest.mark.parametrize("method", ["find", "items"])
@pytest.mark.parametrize("payload", [{"items": {}}, {"items": [None]},
    {"items": [1]}, {"items": [], "nextPageToken": 42},
    {"items": [{"snippet": []}]}])
def test_malformed_playlist_page_fails_with_shape_error(method, payload):
    client = _client_with_responses([payload])
    with pytest.raises(YouTubeApiShapeError):
        if method == "find":
            client.find_playlist_by_title("Queue")
        else:
            client.list_playlist_items(PLAYLIST_ID)


@pytest.mark.parametrize("method", ["find", "items"])
def test_pagination_cycle_stops_before_another_request(method):
    client = _client_with_responses([
        {"items": [], "nextPageToken": "a"},
        {"items": [], "nextPageToken": "b"},
        {"items": [], "nextPageToken": "a"},
    ])
    with pytest.raises(YouTubeApiShapeError, match="repeated"):
        if method == "find":
            client.find_playlist_by_title("Queue")
        else:
            client.list_playlist_items(PLAYLIST_ID)


def test_two_page_items_preserve_order():
    client = _client_with_responses([
        {"items": [ITEM_ONE], "nextPageToken": "next"}, {"items": [ITEM_TWO]}])
    assert [item["video_id"] for item in client.list_playlist_items(PLAYLIST_ID)] == [
        "vid001abc", "vid002def"]


def test_malformed_page_prevents_queue_write_or_delete(tmp_path):
    client = _client_with_responses([
        {"items": [ITEM_ONE], "nextPageToken": "next"}, {"items": [None]}])
    queue = tmp_path / "urls.md"
    with pytest.raises(YouTubeApiShapeError):
        process_capture(client, queue, playlist_id=PLAYLIST_ID)
    assert not queue.exists()


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


@pytest.mark.parametrize("existing", [False, True])
def test_sync_failure_prevents_playlist_delete(tmp_path, monkeypatch, existing):
    queue = tmp_path / "urls.md"
    if existing:
        queue.write_text(canonical_url("vid001abc") + "\n", encoding="utf-8")
    client = _client_with_responses([{"items": [ITEM_ONE]}])
    monkeypatch.setattr(client, "delete_playlist_item", lambda *args: pytest.fail("delete after failed sync"))
    def fail_sync(fd):
        raise OSError("synthetic sync failure")
    monkeypatch.setattr("capture_adapter.os.fsync", fail_sync)
    with pytest.raises(OSError, match="synthetic sync failure"):
        process_capture(client, queue, playlist_id=PLAYLIST_ID)


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


def test_cli_preview_requires_token(tmp_path, monkeypatch):
    monkeypatch.delenv("YOUTUBE_ACCESS_TOKEN", raising=False)
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
        timeout=20,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["error_type"] == "authorization"


@pytest.mark.parametrize("command", ["inspect", "preview", "process"])
def test_cli_routes_commands_without_live_transport(command, tmp_path, monkeypatch, capsys):
    client = _client_with_responses([{"items": [ITEM_ONE]}, {}])
    monkeypatch.setattr(youtube, "YouTubeClient", lambda token: client)
    monkeypatch.setenv("YOUTUBE_ACCESS_TOKEN", "synthetic-test-token")
    queue = tmp_path / "urls.md"
    args = [command, "--playlist-id", PLAYLIST_ID]
    if command != "inspect":
        args.append(str(queue))
    assert youtube.main(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["playlist_id"] == PLAYLIST_ID
    if command == "process":
        assert queue.read_text().strip() == canonical_url("vid001abc")
        assert payload["summary"]["removed_from_playlist"] == 1
    else:
        assert not queue.exists()


@pytest.mark.parametrize("command", ["inspect", "preview", "process"])
def test_cli_network_failure_preserves_queue(command, tmp_path, monkeypatch, capsys):
    client = _client_with_responses([urllib.error.URLError("synthetic network failure")])
    monkeypatch.setattr(youtube, "YouTubeClient", lambda token: client)
    queue = tmp_path / "urls.md"
    queue.write_text("existing evidence\n")
    args = [command, "--access-token", "synthetic-test-token", "--playlist-id", PLAYLIST_ID]
    if command != "inspect":
        args.append(str(queue))
    assert youtube.main(args) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["error_type"] == youtube.YouTubeCaptureError.error_type
    assert "network error" in payload["error"]
    assert queue.read_text() == "existing evidence\n"


def test_client_rejects_json_array_response():
    client = _client_with_responses([[]])
    with pytest.raises(YouTubeApiShapeError, match="top-level"):
        client.list_playlist_items(PLAYLIST_ID)


def test_non_auth_http_error_with_unreadable_body_is_controlled():
    body = MagicMock()
    body.read.side_effect = OSError("synthetic read failure")
    error = urllib.error.HTTPError("https://example.invalid", 500, "Server error", None, body)
    with pytest.raises(youtube.YouTubeCaptureError) as result:
        _client_with_responses([error]).list_playlist_items(PLAYLIST_ID)
    assert type(result.value) is youtube.YouTubeCaptureError


def test_empty_delete_response_succeeds():
    response = _response({})
    response.read.return_value = b""
    client = YouTubeClient("synthetic-test-token", urlopen_fn=lambda *args, **kwargs: response)
    assert client.delete_playlist_item("synthetic-item") is None


@pytest.mark.parametrize("item", [
    {"id": "item", "snippet": {"resourceId": []}},
    {"id": "item", "contentDetails": []},
    {"id": 12, "contentDetails": {"videoId": "video"}},
    {"id": "item", "contentDetails": {"videoId": 12}},
])
def test_invalid_nested_item_data_rejected(item):
    with pytest.raises(YouTubeApiShapeError):
        _client_with_responses([{"items": [item]}]).list_playlist_items(PLAYLIST_ID)


def test_unavailable_item_skipped_without_losing_valid_successor():
    client = _client_with_responses([{"items": [{"id": "unavailable"}, ITEM_ONE]}])
    assert [item["video_id"] for item in client.list_playlist_items(PLAYLIST_ID)] == ["vid001abc"]


def test_find_title_after_empty_page():
    client = _client_with_responses([{"items": [], "nextPageToken": "next"},
        {"items": [{"id": PLAYLIST_ID, "snippet": {"title": "Queue"}}]}])
    assert client.find_playlist_by_title("Queue")["playlist_id"] == PLAYLIST_ID


@pytest.mark.parametrize("title", [None, "Selected queue"])
def test_inspect_resolves_selected_or_default_title(title):
    expected = title or youtube.DEFAULT_QUEUE_TITLE
    client = _client_with_responses([
        {"items": [{"id": PLAYLIST_ID, "snippet": {"title": expected}}]},
        {"items": [ITEM_ONE]},
    ])
    result = inspect_queue(client, playlist_title=title)
    assert result["playlist_id"] == PLAYLIST_ID
    assert result["item_count"] == 1


def test_disappearing_duplicate_stops_before_playlist_delete(tmp_path, monkeypatch):
    queue = tmp_path / "urls.md"
    queue.write_text(canonical_url("vid001abc") + "\n")
    client = _client_with_responses([{"items": [ITEM_ONE]}])

    def removed_before_confirmation(url, path):
        path.write_text("")
        return False

    monkeypatch.setattr(youtube, "confirm_existing_entry", removed_before_confirmation)
    with pytest.raises(YouTubePartialWriteError, match="disappeared"):
        process_capture(client, queue, playlist_id=PLAYLIST_ID)
    assert queue.read_text() == ""


def test_cli_invalid_command_rejected_before_transport(monkeypatch):
    monkeypatch.setattr(youtube, "YouTubeClient", lambda *args: pytest.fail("transport started"))
    with pytest.raises(SystemExit) as result:
        youtube.main(["unsupported-command"])
    assert result.value.code == 2


def test_missing_title_and_missing_match_id_have_controlled_errors():
    with pytest.raises(youtube.YouTubeCaptureError, match="no owned playlist"):
        _client_with_responses([{}]).find_playlist_by_title("Queue")
    with pytest.raises(YouTubeApiShapeError, match="missing id"):
        _client_with_responses([{"items": [{"snippet": {"title": "Queue"}}]}]).find_playlist_by_title("Queue")
