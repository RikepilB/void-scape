"""The observe companion captures only explicit local outputs and sanitizes failures."""
import json
import subprocess
from pathlib import Path

import pytest

import observe


def _completed(argv, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(argv, returncode, stdout, stderr)


def _capture_writer(calls):
    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        Path(argv[-1]).write_bytes(b"captured")
        return _completed(argv)

    return run


def test_doctor_json_reports_windows_capture_and_optional_screenpipe(
        monkeypatch, capsys):
    monkeypatch.setattr(observe, "_system_name", lambda: "windows")
    monkeypatch.setattr(
        observe.shutil, "which", lambda name: f"C:/tools/{name}.exe" if name != "screenpipe" else None,
    )
    monkeypatch.setattr(observe, "_fetch_health", lambda url: None)

    assert observe.main(["doctor", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["meta"] == {"command": "doctor", "protocol_version": "1.0"}
    assert payload["data"]["capture_backend"] == "gdigrab"
    assert payload["data"]["screenpipe"]["reachable"] is False


def test_screenshot_uses_windows_gdigrab_without_shell_or_audio(
        monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(observe, "_system_name", lambda: "windows")
    monkeypatch.setattr(observe.shutil, "which", lambda name: "C:/tools/ffmpeg.exe")
    monkeypatch.setattr(observe.subprocess, "run", _capture_writer(calls))
    output = tmp_path / "screen.png"

    result = observe.screenshot(str(output))

    argv, kwargs = calls[0]
    assert result["path"] == str(output.absolute())
    assert argv[:5] == ["C:/tools/ffmpeg.exe", "-hide_banner", "-loglevel", "error", "-n"]
    assert ["-f", "gdigrab", "-framerate", "1", "-i", "desktop"] == argv[5:11]
    assert argv.count("-i") == 1
    assert kwargs["shell"] is False


def test_clip_uses_linux_x11_display_and_duration(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(observe, "_system_name", lambda: "linux")
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    monkeypatch.setenv("DISPLAY", ":99")
    monkeypatch.setattr(observe.shutil, "which", lambda name: "/usr/bin/ffmpeg")
    monkeypatch.setattr(observe.subprocess, "run", _capture_writer(calls))

    result = observe.clip(str(tmp_path / "screen.mp4"), 7)

    argv, kwargs = calls[0]
    assert result["seconds"] == 7
    assert ["-f", "x11grab", "-framerate", "15", "-i", ":99"] == argv[5:11]
    assert argv[argv.index("-t") + 1] == "7"
    assert argv[argv.index("-c:v") + 1] == "libx264"
    assert argv.count("-i") == 1
    assert kwargs["timeout"] == 37
    assert kwargs["shell"] is False


@pytest.mark.parametrize(
    ("argv", "expected_fragment"),
    [
        (["screenshot", "--out", "capture.jpg", "--json"], ".png"),
        (["clip", "--seconds", "0", "--out", "capture.mp4", "--json"], "between 1 and 300"),
        (["clip", "--seconds", "301", "--out", "capture.mp4", "--json"], "between 1 and 300"),
    ],
)
def test_invalid_capture_input_returns_input_error(argv, expected_fragment, capsys):
    assert observe.main(argv) == 3
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["code"] == "input_error"
    assert expected_fragment in payload["error"]["message"]


def test_existing_destination_is_refused_before_ffmpeg(monkeypatch, tmp_path, capsys):
    output = tmp_path / "existing.png"
    output.write_bytes(b"keep")
    monkeypatch.setattr(
        observe.subprocess, "run", lambda *args, **kwargs: pytest.fail("ffmpeg must not run"),
    )

    assert observe.main(["screenshot", "--out", str(output), "--json"]) == 3

    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["code"] == "input_error"
    assert output.read_bytes() == b"keep"


def test_missing_ffmpeg_is_dependency_error(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(observe, "_system_name", lambda: "windows")
    monkeypatch.setattr(observe.shutil, "which", lambda name: None)

    assert observe.main([
        "screenshot", "--out", str(tmp_path / "capture.png"), "--json",
    ]) == 5
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["code"] == "dependency_error"


@pytest.mark.parametrize(
    ("system", "session_type", "display"),
    [("macos", "", None), ("linux", "wayland", ":0"), ("linux", "x11", None)],
)
def test_unsupported_capture_targets_are_dependency_errors(
        monkeypatch, tmp_path, capsys, system, session_type, display):
    monkeypatch.setattr(observe, "_system_name", lambda: system)
    monkeypatch.setenv("XDG_SESSION_TYPE", session_type)
    if display is None:
        monkeypatch.delenv("DISPLAY", raising=False)
    else:
        monkeypatch.setenv("DISPLAY", display)

    assert observe.main([
        "screenshot", "--out", str(tmp_path / "capture.png"), "--json",
    ]) == 5
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["code"] == "dependency_error"


def test_capture_failure_removes_only_new_partial_and_sanitizes_stderr(
        monkeypatch, tmp_path, capsys):
    output = tmp_path / "partial.png"
    monkeypatch.setattr(observe, "_system_name", lambda: "windows")
    monkeypatch.setattr(observe.shutil, "which", lambda name: "ffmpeg")

    def fail(argv, **kwargs):
        output.write_bytes(b"partial")
        return _completed(argv, returncode=1, stderr="PRIVATE-WINDOW-TITLE")

    monkeypatch.setattr(observe.subprocess, "run", fail)

    assert observe.main(["screenshot", "--out", str(output), "--json"]) == 6
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["code"] == "operation_failed"
    assert "PRIVATE-WINDOW-TITLE" not in json.dumps(payload)
    assert not output.exists()


def test_capture_timeout_is_retryable_and_removes_partial(monkeypatch, tmp_path, capsys):
    output = tmp_path / "partial.mp4"
    monkeypatch.setattr(observe, "_system_name", lambda: "windows")
    monkeypatch.setattr(observe.shutil, "which", lambda name: "ffmpeg")

    def timeout(argv, **kwargs):
        output.write_bytes(b"partial")
        raise subprocess.TimeoutExpired(argv, kwargs["timeout"])

    monkeypatch.setattr(observe.subprocess, "run", timeout)

    assert observe.main([
        "clip", "--seconds", "2", "--out", str(output), "--json",
    ]) == 6
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["retryable"] is True
    assert not output.exists()


@pytest.mark.parametrize(
    "url",
    ["https://127.0.0.1:3030", "http://example.com:3030", "http://user@localhost:3030"],
)
def test_screenpipe_status_rejects_non_loopback_or_credentialed_urls(url, capsys):
    assert observe.main(["status", "--screenpipe-url", url, "--json"]) == 3
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["code"] == "input_error"


def test_screenpipe_native_status_is_whitelisted(monkeypatch):
    monkeypatch.setattr(observe.shutil, "which", lambda name: "screenpipe.exe")
    raw = {
        "running": True,
        "health": {"status": "healthy", "frame_status": "healthy"},
        "last_capture": "recent",
        "secret": "must-not-survive",
    }
    monkeypatch.setattr(
        observe.subprocess,
        "run",
        lambda argv, **kwargs: _completed(argv, stdout=json.dumps(raw)),
    )

    result = observe.screenpipe_status()

    assert result["source"] == "cli"
    assert result["frame_status"] == "healthy"
    assert "secret" not in result


def test_screenpipe_health_fallback_and_absence(monkeypatch):
    monkeypatch.setattr(observe.shutil, "which", lambda name: None)
    monkeypatch.setattr(
        observe, "_fetch_health", lambda url: {"status": "healthy", "audio_status": "disabled"},
    )
    present = observe.screenpipe_status()
    assert present["source"] == "health_endpoint"
    assert present["audio_status"] == "disabled"

    monkeypatch.setattr(observe, "_fetch_health", lambda url: None)
    assert observe.screenpipe_status() == {
        "installed": False, "reachable": False, "source": None,
    }


def test_malformed_native_screenpipe_status_is_sanitized(monkeypatch, capsys):
    monkeypatch.setattr(observe.shutil, "which", lambda name: "screenpipe.exe")
    monkeypatch.setattr(
        observe.subprocess,
        "run",
        lambda argv, **kwargs: _completed(argv, stdout="PRIVATE-NOT-JSON"),
    )

    assert observe.main(["status", "--json"]) == 6
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["code"] == "operation_failed"
    assert "PRIVATE-NOT-JSON" not in json.dumps(payload)


def test_usage_errors_keep_the_standard_envelope(capsys):
    with pytest.raises(SystemExit) as raised:
        observe.main(["screenshot", "--json"])
    assert raised.value.code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["meta"]["command"] == "screenshot"
    assert payload["error"]["code"] == "usage_error"


def test_unexpected_errors_do_not_echo_internal_details(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(observe, "screenshot", lambda *args: (_ for _ in ()).throw(
        RuntimeError("PRIVATE-INTERNAL-DETAIL"),
    ))

    assert observe.main([
        "screenshot", "--out", str(tmp_path / "capture.png"), "--json",
    ]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["message"] == "unexpected observe error"
    assert "PRIVATE-INTERNAL-DETAIL" not in json.dumps(payload)
