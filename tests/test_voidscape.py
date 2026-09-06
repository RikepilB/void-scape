"""Guided Voidscape commands delegate safely to the matching media engine."""
import base64
import json

import pytest

import video
import voidscape
from conftest import requires_ffmpeg


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUB"
    "AScY42YAAAAASUVORK5CYII="
)


@pytest.fixture
def image_carousel(tmp_path):
    folder = tmp_path / "carousel"
    folder.mkdir()
    for name in ("slide10.png", "slide2.png", "slide1.png"):
        (folder / name).write_bytes(PNG_1X1)
    return folder


@pytest.fixture
def mixed_image_carousel(tmp_path):
    folder = tmp_path / "mixed"
    folder.mkdir()
    (folder / "slide1.png").write_bytes(PNG_1X1)
    (folder / "notes.txt").write_text("not an image", encoding="utf-8")
    (folder / "nested").mkdir()
    return folder


def test_empty_guided_cli_shows_welcome_and_next_step(capsys):
    assert voidscape.main([]) == 0

    welcome = capsys.readouterr().out
    assert "VOIDSCAPE" in welcome
    assert "inspect <file-or-url>" in welcome
    assert "voidscape init" in welcome
    assert 'voidscape inspect "meeting.mp4"' in welcome


def test_init_installs_primary_agent_skill_without_approving_remote_work(
        tmp_path, capsys):
    codex_root = tmp_path / "codex"
    agents_root = tmp_path / "agents"

    assert voidscape.main([
        "init",
        "--codex-skills-root", str(codex_root),
        "--agents-skills-root", str(agents_root),
        "--json",
    ]) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["cli"] == "voidscape"
    assert result["cloud_approved"] is False
    assert result["model_download_approved"] is False
    for root in (codex_root, agents_root):
        assert (root / "voidscape" / "SKILL.md").is_file()
        assert (root / "voidscape" / "scripts" / "voidscape.py").is_file()


def test_init_preserves_existing_agent_workspace(tmp_path):
    codex_root = tmp_path / "codex"
    agents_root = tmp_path / "agents"
    destination = codex_root / "voidscape"
    destination.mkdir(parents=True)
    workspace = destination / "workspace.json"
    workspace.write_text('{"inbox_dir": "keep-me"}', encoding="utf-8")

    assert voidscape.main([
        "init",
        "--codex-skills-root", str(codex_root),
        "--agents-skills-root", str(agents_root),
        "--json",
    ]) == 0

    assert workspace.read_text(encoding="utf-8") == '{"inbox_dir": "keep-me"}'


def test_init_can_skip_agent_skill_install(tmp_path, capsys):
    codex_root = tmp_path / "codex"
    agents_root = tmp_path / "agents"

    assert voidscape.main([
        "init", "--no-skill",
        "--codex-skills-root", str(codex_root),
        "--agents-skills-root", str(agents_root),
        "--json",
    ]) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["agent_skills"] == []
    assert not codex_root.exists()
    assert not agents_root.exists()


def test_init_explains_how_to_install_missing_windows_media_tools(
        tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(voidscape.shutil, "which", lambda _name: None)
    monkeypatch.setattr(voidscape.platform, "system", lambda: "Windows")

    assert voidscape.main([
        "init", "--no-skill", "--json",
        "--codex-skills-root", str(tmp_path / "codex"),
        "--agents-skills-root", str(tmp_path / "agents"),
    ]) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["ready_for_video"] is False
    assert result["ffmpeg_install"] == "winget install --id=Gyan.FFmpeg -e"


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
    assert set(report["observe"]) == {"capture_supported", "backend", "screenpipe_optional"}
    assert report["observe"]["screenpipe_optional"] is True


@requires_ffmpeg
def test_guided_image_inspect_and_preview_show_local_carousel(image_carousel, capsys):
    assert voidscape.main(["inspect", str(image_carousel)]) == 0
    inspected = capsys.readouterr().out
    assert "Carousel: 3 images" in inspected
    assert "slide1.png, slide2.png, slide10.png" in inspected

    assert voidscape.main(["preview", str(image_carousel)]) == 0
    previewed = capsys.readouterr().out
    assert "Voidscape preview" in previewed
    assert "image tokens:" in previewed
    assert "prepared locally" in previewed


@requires_ffmpeg
def test_guided_image_inspect_and_preview_name_skipped_entries(
        mixed_image_carousel, capsys):
    assert voidscape.main(["inspect", str(mixed_image_carousel)]) == 0
    inspected = capsys.readouterr().out
    assert "notes.txt (unsupported)" in inspected
    assert "nested (not a file)" in inspected

    assert voidscape.main(["preview", str(mixed_image_carousel)]) == 0
    previewed = capsys.readouterr().out
    assert "notes.txt (unsupported)" in previewed
    assert "nested (not a file)" in previewed

    assert voidscape.main([
        "preview", str(mixed_image_carousel), "--json",
    ]) == 0
    structured = json.loads(capsys.readouterr().out)
    assert {
        item["name"]: item["reason"] for item in structured["skipped"]
    } == {
        "notes.txt": "unsupported",
        "nested": "not a file",
    }


@requires_ffmpeg
def test_guided_image_preview_uses_workspace_agent_model(
        image_carousel, tmp_path, capsys):
    config = tmp_path / "workspace.json"
    config.write_text(
        json.dumps({"agent_model": "gpt-5.6-luna"}),
        encoding="utf-8",
    )

    assert voidscape.main([
        "preview", str(image_carousel), "--config", str(config), "--json",
    ]) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["agent_model"] == "gpt-5.6-luna"


@requires_ffmpeg
def test_guided_image_read_writes_evidence_and_image_citation_guidance(
        image_carousel, tmp_path, capsys):
    workdir = tmp_path / "evidence"

    assert voidscape.main([
        "read", str(image_carousel), "--workdir", str(workdir),
    ]) == 0

    output = capsys.readouterr().out
    assert "Images: 3" in output
    assert "[image 1]" in output
    assert (workdir / "manifest.json").exists()


@requires_ffmpeg
def test_guided_video_input_never_calls_image_engine(static_clip, monkeypatch, capsys):
    def unexpected_image_probe(_input):
        raise AssertionError("video input dispatched to image engine")

    monkeypatch.setattr(voidscape.image_engine, "probe", unexpected_image_probe)

    assert voidscape.main(["inspect", str(static_clip)]) == 0
    assert "Suggested scope" in capsys.readouterr().out
