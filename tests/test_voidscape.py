"""Guided Voidscape commands delegate safely to the stable read-video engine."""
import json
from pathlib import Path

import pytest

import video
import voidscape
from conftest import requires_ffmpeg


def test_empty_guided_cli_shows_welcome_and_next_step(capsys):
    assert voidscape.main([]) == 0

    welcome = capsys.readouterr().out
    assert "VOIDSCAPE" in welcome
    assert "inspect <file-or-url>" in welcome
    assert 'voidscape.py inspect "meeting.mp4"' in welcome


def test_customize_previews_without_writing(tmp_path, capsys):
    config = tmp_path / "workspace.json"

    assert voidscape.main([
        "customize", "--config", str(config), "--inbox", str(tmp_path / "inbox"),
        "--library", str(tmp_path / "library"),
    ]) == 0

    assert not config.exists()
    assert "No files changed" in capsys.readouterr().out


def test_customize_writes_only_with_yes_and_explicit_directory_creation(tmp_path):
    config = tmp_path / "workspace.json"
    inbox, library = tmp_path / "inbox", tmp_path / "library"

    assert voidscape.main([
        "customize", "--config", str(config), "--inbox", str(inbox),
        "--library", str(library), "--create-dirs", "--yes",
    ]) == 0

    saved = json.loads(config.read_text(encoding="utf-8"))
    assert saved["inbox_dir"] == str(inbox)
    assert saved["out_dir"] == str(library)
    assert inbox.is_dir() and library.is_dir()


def test_customize_imports_legacy_only_after_confirmation(tmp_path, capsys):
    legacy = tmp_path / "read-video-workspace.json"
    legacy.write_text(json.dumps({"inbox_dir": "old-inbox", "out_dir": "old-library"}), encoding="utf-8")
    config = tmp_path / "voidscape-workspace.json"

    assert voidscape.main([
        "customize", "--config", str(config), "--import-read-video", str(legacy),
    ]) == 0

    assert not config.exists()
    assert "Legacy config considered" in capsys.readouterr().out


def test_video_honors_compatibility_workspace_environment(tmp_path, monkeypatch):
    config = tmp_path / "legacy-workspace.json"
    config.write_text(json.dumps({"inbox_dir": "compat-inbox"}), encoding="utf-8")
    monkeypatch.setenv("VOIDSCAPE_WORKSPACE_PATH", str(config))

    assert video.load_workspace() == {"inbox_dir": "compat-inbox"}


@requires_ffmpeg
def test_inspect_and_preview_follow_existing_engine(static_clip, tmp_path, capsys):
    assert voidscape.main(["inspect", str(static_clip)]) == 0
    inspected = capsys.readouterr().out
    assert "Suggested scope" in inspected

    assert voidscape.main([
        "preview", str(static_clip), "--tier", "visual", "--config", str(tmp_path / "missing.json"),
    ]) == 0
    previewed = capsys.readouterr().out
    assert "Voidscape preview" in previewed
    assert "TOTAL:" in previewed


def test_doctor_json_is_non_interactive_and_structured(capsys, tmp_path):
    assert voidscape.main(["doctor", "--config", str(tmp_path / "missing.json"), "--json"]) in (0, 5)
    report = json.loads(capsys.readouterr().out)
    assert report["workspace_configured"] is False
    assert {"ffmpeg", "ffprobe", "yt-dlp"}.issubset(report["tools"])
