"""Codex plugin packaging stays self-contained and synchronized."""
import json
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parent.parent
PLUGIN = REPO / "plugins" / "voidscape"
MANIFEST = PLUGIN / ".codex-plugin" / "plugin.json"


def _builder(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("plugin_builder", REPO / "scripts/build-plugin.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = tmp_path / "source"
    source.mkdir()
    (source / "SKILL.md").write_text("new", encoding="utf-8")
    destination = tmp_path / "output/skill"
    destination.mkdir(parents=True)
    monkeypatch.setattr(module, "SOURCE", source)
    monkeypatch.setattr(module, "DESTINATION", destination)
    return module, destination


def test_sync_rejects_destination_symlink_before_writing(tmp_path, monkeypatch):
    module, destination = _builder(tmp_path, monkeypatch)
    outside = tmp_path / "outside.txt"
    outside.write_text("private", encoding="utf-8")
    try:
        (destination / "SKILL.md").symlink_to(outside)
    except OSError:
        pytest.skip("host does not permit test symlinks")
    with pytest.raises(RuntimeError, match="symlinks"):
        module.sync()
    assert outside.read_text(encoding="utf-8") == "private"
    assert not list(destination.parent.glob(".plugin-stage-*"))


def test_sync_swaps_staged_tree_and_preserves_original(tmp_path, monkeypatch):
    module, destination = _builder(tmp_path, monkeypatch)
    (destination / "SKILL.md").write_text("old", encoding="utf-8")
    module.sync()
    assert module.check() == []
    previous = list(destination.parent.glob(".plugin-stage-*/previous/SKILL.md"))
    assert len(previous) == 1
    assert previous[0].read_text(encoding="utf-8") == "old"


def test_staging_failure_preserves_live_tree(tmp_path, monkeypatch):
    module, destination = _builder(tmp_path, monkeypatch)
    (destination / "SKILL.md").write_text("old", encoding="utf-8")
    def fail_copy(*args, **kwargs):
        raise OSError("simulated disk failure")
    monkeypatch.setattr(module._Directory, "write", fail_copy)
    with pytest.raises(OSError, match="disk failure"):
        module.sync()
    assert (destination / "SKILL.md").read_text(encoding="utf-8") == "old"


def test_source_replaced_after_stat_cannot_read_outside(tmp_path, monkeypatch):
    module, destination = _builder(tmp_path, monkeypatch)
    outside = tmp_path / "private.txt"
    outside.write_text("private", encoding="utf-8")
    source_file = module.SOURCE / "SKILL.md"
    original_read = module._Directory.read

    def swap_before_read(directory, name):
        if directory.path == module.SOURCE and name == "SKILL.md":
            source_file.rename(module.SOURCE / "original.md")
            try:
                source_file.symlink_to(outside)
            except OSError:
                pytest.skip("host does not permit test symlinks")
        return original_read(directory, name)

    monkeypatch.setattr(module._Directory, "read", swap_before_read)
    with pytest.raises((OSError, RuntimeError)):
        module.sync()
    assert not (destination / "SKILL.md").exists()
    assert not list(destination.parent.glob(".plugin-stage-*"))


def test_publish_failure_restores_previous_tree(tmp_path, monkeypatch):
    module, destination = _builder(tmp_path, monkeypatch)
    (destination / "SKILL.md").write_text("old", encoding="utf-8")
    original_rename = module._Directory.rename

    def fail_publish(directory, name, target, target_name):
        if name == "replacement":
            raise OSError("publish failed")
        return original_rename(directory, name, target, target_name)

    monkeypatch.setattr(module._Directory, "rename", fail_publish)
    with pytest.raises(OSError, match="publish failed"):
        module.sync()
    assert (destination / "SKILL.md").read_text(encoding="utf-8") == "old"


def test_destination_parent_replacement_cannot_redirect_writes(tmp_path, monkeypatch):
    module, destination = _builder(tmp_path, monkeypatch)
    outside = tmp_path / "outside"
    outside.mkdir()
    original_mkdir = module._Directory.mkdir
    attempted = []

    def swap_before_stage(directory, name):
        if directory.path == destination.parent and name.startswith(".plugin-stage-"):
            attempted.append(True)
            try:
                destination.parent.rename(tmp_path / "original-output")
            except PermissionError:
                # Windows handles intentionally deny directory replacement.
                pass
            else:
                try:
                    destination.parent.symlink_to(outside, target_is_directory=True)
                except OSError:
                    pytest.skip("host does not permit test symlinks")
        return original_mkdir(directory, name)

    monkeypatch.setattr(module._Directory, "mkdir", swap_before_stage)
    module.sync()
    assert attempted
    assert list(outside.iterdir()) == []
    output = tmp_path / "original-output" if (tmp_path / "original-output").exists() else destination.parent
    assert (output / "skill/SKILL.md").read_text(encoding="utf-8") == "new"


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
