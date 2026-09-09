"""Contract tests for the shared capture-adapter module."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from capture_adapter import (
    ACTION_APPEND,
    ACTION_SKIP_DUPLICATE,
    CaptureAdapter,
    CaptureAuthError,
    CaptureError,
    CapturePartialWriteError,
    append_and_confirm,
    durable_append_or_raise,
    emit_capture_error,
    is_duplicate,
    preview_action_for_url,
    queue_append_result,
)


class _FakeAdapter:
    """Minimal in-memory adapter exercising the shared queue contract."""

    def __init__(self, urls: list[str]) -> None:
        self._urls = list(urls)

    def inspect(self) -> dict:
        return {"item_count": len(self._urls), "items": [{"url": u} for u in self._urls]}

    def preview(self, urls_md_path: Path) -> dict:
        planned = []
        for url in self._urls:
            duplicate, action = preview_action_for_url(url, urls_md_path)
            planned.append({"url": url, "duplicate": duplicate, "action": action})
        return {
            "items": planned,
            "mutates_urls_md": False,
            "mutates_source": False,
        }

    def process(self, urls_md_path: Path) -> dict:
        preview = self.preview(urls_md_path)
        processed = []
        for item in preview["items"]:
            write = queue_append_result(item["url"], urls_md_path)
            processed.append({"url": item["url"], **write})
        return {"processed": processed, "aborted": False}


def test_fake_adapter_satisfies_protocol():
    adapter = _FakeAdapter(["https://example.com/a"])
    assert isinstance(adapter, CaptureAdapter)


def test_is_duplicate_and_append_round_trip(tmp_path):
    urls_md = tmp_path / "urls.md"
    url = "https://example.com/watch?v=abc"
    assert is_duplicate(url, urls_md) is False
    assert append_and_confirm(url, urls_md) is True
    assert is_duplicate(url, urls_md) is True


def test_preview_action_for_url(tmp_path):
    urls_md = tmp_path / "urls.md"
    url = "https://example.com/item"
    assert preview_action_for_url(url, urls_md) == (False, ACTION_APPEND)
    append_and_confirm(url, urls_md)
    assert preview_action_for_url(url, urls_md) == (True, ACTION_SKIP_DUPLICATE)


def test_append_flushes_and_syncs_before_confirmation(tmp_path, monkeypatch):
    queue = tmp_path / "urls.md"
    url = "https://example.com/item"
    events = []
    real_sync = os.fsync
    real_read = Path.read_text

    def sync(fd):
        assert queue.read_bytes() == (url + os.linesep).encode()
        events.append("sync")
        real_sync(fd)

    def read(path, *args, **kwargs):
        events.append("confirm")
        return real_read(path, *args, **kwargs)

    monkeypatch.setattr("capture_adapter.os.fsync", sync)
    monkeypatch.setattr(Path, "read_text", read)
    assert append_and_confirm(url, queue)
    assert events == ["sync", "confirm"]


def test_sync_failure_never_reports_success(tmp_path, monkeypatch):
    def fail_sync(fd):
        raise OSError("synthetic sync failure")
    monkeypatch.setattr("capture_adapter.os.fsync", fail_sync)
    with pytest.raises(OSError, match="synthetic sync failure"):
        queue_append_result("https://example.com/item", tmp_path / "urls.md")
    # Visible bytes from the failed attempt cannot make its retry safe.
    with pytest.raises(OSError, match="synthetic sync failure"):
        queue_append_result("https://example.com/item", tmp_path / "urls.md")


@pytest.mark.parametrize("url", ["", " https://example.com", "https://example.com\nother", "a\rb", "a\x00b"])
def test_invalid_entry_never_creates_queue(tmp_path, url):
    queue = tmp_path / "urls.md"
    with pytest.raises(ValueError, match="single-line"):
        append_and_confirm(url, queue)
    assert not queue.exists()


def test_queue_append_result_skips_duplicate(tmp_path):
    urls_md = tmp_path / "urls.md"
    url = "https://example.com/item"
    append_and_confirm(url, urls_md)
    assert queue_append_result(url, urls_md) == {"duplicate": True, "appended": False}


def test_durable_append_or_raise_on_failure(tmp_path, monkeypatch):
    urls_md = tmp_path / "urls.md"
    url = "https://example.com/fail"

    def fail_append(u: str, p: Path) -> bool:
        return False

    monkeypatch.setattr("capture_adapter.append_and_confirm", fail_append)
    with pytest.raises(CapturePartialWriteError) as exc:
        durable_append_or_raise(url, urls_md)
    assert exc.value.error_type == "partial_write"


def test_emit_capture_error_json(capsys):
    err = CaptureAuthError("missing token", details={"field": "access_token"})
    code = emit_capture_error(err)
    assert code == 1
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload == {
        "error": "missing token",
        "error_type": "authorization",
        "details": {"field": "access_token"},
    }


def test_fake_adapter_preview_does_not_mutate_urls_md(tmp_path):
    urls_md = tmp_path / "urls.md"
    adapter = _FakeAdapter(
        ["https://example.com/new", "https://example.com/new"],
    )
    urls_md.write_text("https://example.com/new\n", encoding="utf-8")
    result = adapter.preview(urls_md)
    assert result["mutates_urls_md"] is False
    assert all(item["action"] == ACTION_SKIP_DUPLICATE for item in result["items"])
    assert urls_md.read_text(encoding="utf-8").count("\n") == 1


def test_fake_adapter_process_appends_only_new_urls(tmp_path):
    urls_md = tmp_path / "urls.md"
    adapter = _FakeAdapter(
        ["https://example.com/existing", "https://example.com/fresh"],
    )
    urls_md.write_text("https://example.com/existing\n", encoding="utf-8")
    result = adapter.process(urls_md)
    lines = urls_md.read_text(encoding="utf-8").splitlines()
    assert lines == ["https://example.com/existing", "https://example.com/fresh"]
    assert result["processed"][0]["duplicate"] is True
    assert result["processed"][1]["appended"] is True


def test_capture_error_types_are_stable():
    assert CaptureError("x").error_type == "capture_error"
    assert CapturePartialWriteError("x").error_type == "partial_write"
