"""Packaging checks do not claim live agent or browser validation."""
from pathlib import Path
import json
import shutil

import pytest

import sync_instagram_roles as sync


ROOT = Path(__file__).resolve().parents[1]


def test_project_harness_outputs_match_canonical_roles():
    for path, expected in sync.rendered_files(ROOT).items():
        assert path.read_text(encoding='utf-8') == expected, str(path)


def test_check_reports_drift_without_writing(tmp_path, monkeypatch, capsys):
    source = Path('.agents/skills/instagram-triage')
    shutil.copytree(ROOT / source, tmp_path / source)
    monkeypatch.setattr(sync, 'ROOT', tmp_path)
    assert sync.main([]) == 1
    assert not (tmp_path / '.claude').exists()
    assert sync.main(['--write']) == 0
    assert sync.main([]) == 0
    target = tmp_path / '.claude/skills/instagram-triage/SKILL.md'
    target.write_text('local drift', encoding='utf-8')
    assert sync.main([]) == 1
    assert target.read_text(encoding='utf-8') == 'local drift'
    assert 'SKILL.md' in capsys.readouterr().out


def test_registry_rejects_unowned_paths_before_writes(tmp_path, monkeypatch):
    source = Path('.agents/skills/instagram-triage')
    shutil.copytree(ROOT / source, tmp_path / source)
    registry = tmp_path / source / 'roles.json'
    roles = json.loads(registry.read_text(encoding='utf-8'))
    roles[0]['instructions'] = '../../outside.md'
    registry.write_text(json.dumps(roles), encoding='utf-8')
    monkeypatch.setattr(sync, 'ROOT', tmp_path)
    with pytest.raises(ValueError, match='unknown role instructions'):
        sync.main(['--write'])
    assert not (tmp_path / '.claude').exists()
