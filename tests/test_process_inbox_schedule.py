import json
from pathlib import Path
import subprocess
import sys

import pytest

import process_inbox_schedule as schedule


@pytest.fixture
def roots(tmp_path):
    root = tmp_path / 'inbox'
    notes = tmp_path / 'notes'
    configs = tmp_path / 'configs'
    root.mkdir()
    notes.mkdir()
    configs.mkdir()
    return root, notes, configs / 'inbox-schedule.json'


def config_for(roots, **changes):
    root, notes, path = roots
    settings = {'root': root, 'notes_root': notes, 'model': 'cached-model', 'config': path}
    settings.update(changes)
    return schedule.plan(**settings)


def test_preview_is_read_only_and_exposes_manual_registration(roots):
    config = config_for(roots)
    result = schedule.preview(config)
    assert result['mode'] == 'preview' and result['changes'] is False
    assert not Path(config['task']['config']).exists()
    assert 'schtasks.exe' in result['registration_command']
    assert '/SC MINUTE' in result['registration_command']
    assert '--run' in result['registration_command']
    assert '--allow-cloud' not in result['registration_command']
    assert 'never invokes' in result['registration_notice']


def test_plan_requires_local_paths_and_a_recovery_interval(roots):
    root, notes, path = roots
    with pytest.raises(ValueError, match='existing inbox'):
        schedule.plan(root / 'missing', notes, 'cached', config=path)
    with pytest.raises(ValueError, match='local'):
        schedule.plan(root, notes, 'cached', backend='openai', config=path)
    with pytest.raises(ValueError, match='40 minutes'):
        schedule.plan(root, notes, 'cached', limit=3, timeout=600, interval_minutes=39, config=path)
    with pytest.raises(ValueError, match='outside the inbox'):
        schedule.plan(root, notes, 'cached', config=root / 'schedule.json')
    with pytest.raises(ValueError, match='timeout or quiet period'):
        schedule.plan(root, notes, 'cached', timeout=True, config=path)


def test_write_config_is_idempotent_but_never_replaces_different_settings(roots):
    config = config_for(roots)
    result = schedule.write_config(config)
    path = Path(result['config'])
    stored = json.loads(path.read_text(encoding='utf-8'))
    assert result['mode'] == 'written' and stored == config
    assert 'No task was created' in result['registration_notice']
    schedule.write_config(config)
    changed = config_for(roots, task_name='Different task')
    with pytest.raises(ValueError, match='refusing overwrite'):
        schedule.write_config(changed)


def test_run_records_only_sanitized_counts(monkeypatch, roots):
    config = config_for(roots)
    path = Path(schedule.write_config(config)['config'])
    captured = {}

    def completed(command, **kwargs):
        captured['command'] = command
        captured['kwargs'] = kwargs
        return subprocess.CompletedProcess(command, 0, json.dumps({'ok': True, 'data': {
            'mode': 'apply', 'processed': 1, 'skipped': 2, 'failed': 0, 'deferred': 3,
            'results': [{'source': 'private recording', 'note': 'private note'}],
        }, 'error': None}))

    monkeypatch.setattr(schedule.subprocess, 'run', completed)
    summary = schedule.run(path)
    assert summary['status'] == 'completed'
    assert {field: summary[field] for field in ('processed', 'skipped', 'failed', 'deferred')} == {
        'processed': 1, 'skipped': 2, 'failed': 0, 'deferred': 3,
    }
    assert '--apply' in captured['command'] and '--allow-cloud' not in captured['command']
    assert captured['command'][0] == sys.executable
    assert all(part.casefold() != 'schtasks.exe' for part in captured['command'])
    assert captured['kwargs']['stdin'] is subprocess.DEVNULL
    line = Path(config['task']['log']).read_text(encoding='utf-8')
    assert 'private recording' not in line and 'private note' not in line


def test_run_sanitizes_controller_failure_and_timeout(monkeypatch, roots):
    config = config_for(roots)
    path = Path(schedule.write_config(config)['config'])
    monkeypatch.setattr(schedule.subprocess, 'run', lambda *args, **kwargs: subprocess.CompletedProcess(args, 6, 'private trace'))
    assert schedule.run(path)['status'] == 'failed'
    monkeypatch.setattr(schedule.subprocess, 'run', lambda *args, **kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired(args[0], 1)))
    assert schedule.run(path)['status'] == 'failed'
    log = Path(config['task']['log']).read_text(encoding='utf-8')
    assert 'private trace' not in log


def test_tampered_executable_paths_do_not_run(monkeypatch, roots):
    config = config_for(roots)
    path = Path(schedule.write_config(config)['config'])
    raw = json.loads(path.read_text(encoding='utf-8'))
    raw['task']['controller'] = str(path)
    path.write_text(json.dumps(raw), encoding='utf-8')
    monkeypatch.setattr(schedule.subprocess, 'run', lambda *args, **kwargs: pytest.fail('tampered config must not execute'))
    with pytest.raises(ValueError, match='executable paths changed'):
        schedule.run(path)
    assert not Path(config['task']['log']).exists()
