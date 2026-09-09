"""Legacy Windows code pages must not lose Unicode CLI output or errors."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

import video


SCRIPTS = Path(__file__).resolve().parents[1] / "skill" / "scripts"


@pytest.mark.parametrize("module", ["voidscape", "video", "image", "article", "chat"])
def test_entrypoint_reconfigures_legacy_streams(module):
    code = (
        f"import {module} as cli, sys, json; "
        "sys.platform = 'win32'; "
        "sys.stdout.reconfigure(encoding='cp1252'); "
        "sys.stderr.reconfigure(encoding='cp1252'); "
        "\ntry: cli.main(['--help'])\nexcept SystemExit: pass\n"
        "print(json.dumps({'title': '日本語 🎬'}, ensure_ascii=False)); "
        "print('日本語 🎬', file=sys.stderr)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=SCRIPTS,
        env={**os.environ, "PYTHONIOENCODING": "cp1252"},
        capture_output=True, check=False,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    assert json.loads(result.stdout.decode("utf-8").splitlines()[-1]) == {
        "title": "日本語 🎬",
    }
    assert result.stderr.decode("utf-8").strip() == "日本語 🎬"


def test_unconfigurable_capture_streams_are_supported(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "stdout", io.StringIO())
    monkeypatch.setattr(sys, "stderr", io.StringIO())
    video.configure_cli_streams()
    print("日本語")
    assert sys.stdout.getvalue() == "日本語\n"


def test_guided_read_unicode_filename_under_legacy_encoding(tmp_path):
    source = tmp_path / "日本語.md"
    source.write_text("# 日本語\n\nLocal evidence.\n", encoding="utf-8")
    destination = tmp_path / "証拠"
    code = (
        "import voidscape, sys; sys.platform = 'win32'; "
        "sys.exit(voidscape.main(sys.argv[1:]))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code, "read", str(source), "--reader", "article",
         "--workdir", str(destination), "--json"],
        cwd=SCRIPTS, env={**os.environ, "PYTHONIOENCODING": "cp1252"},
        capture_output=True, check=False,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    payload = json.loads(result.stdout.decode("utf-8"))
    assert payload["workdir"] == str(destination.resolve())
    assert json.loads((destination / "manifest.json").read_text(encoding="utf-8")) == payload


def test_stream_reconfiguration_failure_is_nonfatal(monkeypatch):
    class LockedStream:
        def reconfigure(self, **kwargs):
            raise ValueError("stream already read")

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "stdout", LockedStream())
    monkeypatch.setattr(sys, "stderr", LockedStream())
    video.configure_cli_streams()


def test_non_windows_streams_are_unchanged(monkeypatch):
    output = io.TextIOWrapper(io.BytesIO(), encoding="ascii")
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(sys, "stdout", output)
    video.configure_cli_streams()
    assert output.encoding == "ascii"
