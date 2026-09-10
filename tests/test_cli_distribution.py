"""Distribution contract for the installable Voidscape CLI."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent


def test_pyproject_exposes_voidscape_console_script():
    project = (REPO / "pyproject.toml").read_text(encoding="utf-8")

    assert 'name = "voidscape"' in project
    assert 'voidscape = "skill.scripts.voidscape:main"' in project
    assert 'dependencies = ["yt-dlp>=2026.8.19"]' in project


def test_packaged_module_help_uses_global_command_name():
    result = subprocess.run(
        [sys.executable, "-m", "skill.scripts.voidscape", "--help"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "usage: voidscape" in result.stdout
    assert "{init,inspect,preview,read,batch-preview,batch-read,customize,doctor,route,sources}" in result.stdout


def test_public_beginner_paths_use_the_global_cli_without_a_clone():
    paths = (
        REPO / "README.md",
        REPO / "docs" / "index.html",
        REPO / "docs" / "guide.html",
        REPO / "docs" / "agents" / "install.md",
    )

    for path in paths:
        content = path.read_text(encoding="utf-8")
        assert "voidscape init" in content
        assert "archive/refs/heads/main.zip" in content
        assert "git clone https://github.com/RikepilB/void-scape.git" not in content
        assert ".\\scripts\\install-skill.ps1" not in content
        assert "bash scripts/install-skill.sh" not in content
