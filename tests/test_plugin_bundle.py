"""Codex plugin packaging stays self-contained and synchronized."""
import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
PLUGIN = REPO / "plugins" / "voidscape"
MANIFEST = PLUGIN / ".codex-plugin" / "plugin.json"


def test_plugin_manifest_has_real_metadata_and_no_unshipped_components():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert manifest["name"] == "voidscape"
    assert manifest["version"] == "0.1.0"
    assert manifest["skills"] == "./skills/"
    assert manifest["author"]["name"] == "Richard Pillaca"
    assert manifest["interface"]["displayName"] == "Voidscape"
    assert isinstance(manifest["interface"]["defaultPrompt"], list)
    assert 1 <= len(manifest["interface"]["defaultPrompt"]) <= 3
    assert "mcpServers" not in manifest
    assert "apps" not in manifest
    assert "hooks" not in manifest


def test_plugin_contains_the_primary_skill_without_private_config():
    bundled = PLUGIN / "skills" / "voidscape"

    assert (bundled / "SKILL.md").is_file()
    assert (bundled / "scripts" / "voidscape.py").is_file()
    assert not (bundled / "workspace.json").exists()
    assert not list(bundled.rglob("*.pyc"))
    assert not list(bundled.rglob("__pycache__"))
    assert not list(bundled.rglob(".env*"))
    assert not list(bundled.rglob("*.key"))
    assert not list(bundled.rglob("*.pem"))
    assert not any(path.is_symlink() for path in bundled.rglob("*"))


def test_plugin_skill_matches_the_canonical_skill_tree():
    result = subprocess.run(
        [sys.executable, "scripts/build-plugin.py", "--check"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
