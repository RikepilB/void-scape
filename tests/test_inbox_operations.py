import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

import process_inbox as inbox
from sync_inbox_skill import ROOT, rendered_files
from triage_store import locked


def test_recent_recording_or_sidecar_waits(tmp_path):
    source = tmp_path / 'clip.mp4'
    source.write_bytes(b'fixture')
    os.utime(source, (1000, 1000))
    assert inbox.settled(source, 60, now=1060)
    sidecar = source.with_suffix('.srt')
    sidecar.write_text('still copying')
    os.utime(sidecar, (1050, 1050))
    assert not inbox.settled(source, 60, now=1060)
    assert inbox.settled(source, 60, now=1110)


def test_zero_quiet_period_disables_future_timestamp_deferral(tmp_path):
    source = tmp_path / 'clip.mp4'
    source.write_bytes(b'complete selected fixture')
    os.utime(source, (5000, 5000))
    assert inbox.settled(source, 0, now=1000)
    assert not inbox.settled(source, 60, now=1000)


def test_worker_rechecks_changed_file_before_hashing_or_generation(tmp_path):
    source = tmp_path / 'clip.mp4'
    source.write_bytes(b'fixture')
    os.utime(source, (1, 1))
    assert inbox.discover(tmp_path, 1, min_age=60) == [source]
    os.utime(source, None)
    result = inbox.process_one(tmp_path, tmp_path.parent / 'notes', source, 'cached', 'auto', 11434,
                               producer=lambda *a: pytest.fail('recent file must wait'), min_age=60)
    assert result['status'] == 'deferred'
    assert not (tmp_path / '.inbox').exists()


def test_default_preview_waits_without_creating_state(tmp_path):
    source = tmp_path / 'clip.mp4'
    source.write_bytes(b'fixture')
    result = inbox.process(tmp_path, tmp_path.parent / 'notes', 'cached')
    assert result['selected'] == [] and result['min_age'] == 60
    assert sorted(path.name for path in tmp_path.iterdir()) == ['clip.mp4']


def test_actual_contended_lock_reports_busy_without_worker(tmp_path):
    root = tmp_path / 'inbox'
    root.mkdir()
    with locked(root / '.inbox'):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/process_inbox.py'),
                                 '--root', str(root), '--notes-root', str(tmp_path / 'notes'),
                                 '--model', 'cached', '--apply'], capture_output=True,
                                text=True, encoding='utf-8', timeout=15)
    value = json.loads(result.stdout)
    assert result.returncode == 0 and value['ok'] is True
    assert value['data']['status'] == 'busy' and value['data']['failed'] == 0
    assert not (root / '.inbox/runs').exists()


def test_filesystem_permission_error_is_not_reported_as_busy(tmp_path, monkeypatch):
    def denied(*args):
        raise PermissionError('directory denied')
    monkeypatch.setattr(inbox, 'locked', denied)
    with pytest.raises(PermissionError):
        inbox.process(tmp_path, tmp_path.parent / 'notes', 'cached', apply=True)


def test_busy_run_does_not_scan_files_being_moved(tmp_path, monkeypatch):
    monkeypatch.setattr(inbox, 'discover', lambda *a, **kw: pytest.fail('busy run must not scan changing input'))
    with locked(tmp_path / '.inbox'):
        assert inbox.process(tmp_path, tmp_path.parent / 'notes', 'cached', apply=True)['status'] == 'busy'


def test_missing_inbox_is_not_created_during_apply(tmp_path):
    root = tmp_path / 'missing'
    with pytest.raises(ValueError, match='existing inbox'):
        inbox.process(root, tmp_path / 'notes', 'cached', apply=True)
    assert not root.exists()


@pytest.mark.parametrize('limit', [0, 101])
def test_invalid_limit_does_not_create_lock_state(tmp_path, limit):
    with pytest.raises(ValueError, match='settings'):
        inbox.process(tmp_path, tmp_path.parent / 'notes', 'cached', apply=True, limit=limit)
    assert not (tmp_path / '.inbox').exists()


def test_project_skill_and_role_mirrors_match():
    for path, content in rendered_files(ROOT).items():
        assert path.read_text(encoding='utf-8') == content, path


@pytest.mark.parametrize('age', [-1, float('nan'), float('inf'), 86401])
def test_invalid_quiet_period_cannot_create_state(tmp_path, age):
    with pytest.raises(ValueError):
        inbox.process(tmp_path, tmp_path.parent / 'notes', 'cached', apply=True, min_age=age)
    assert not (tmp_path / '.inbox').exists()
