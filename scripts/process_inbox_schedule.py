"""Render or run a bounded, local-only Process Inbox scheduler configuration."""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone

from process_inbox import LOCAL
from triage_store import checked, encoded, exclusive


REPO = Path(__file__).resolve().parents[1]
SCHEMA = 1
DEFAULT_TASK_NAME = 'Voidscape Process Inbox'
MODEL = re.compile(r'[A-Za-z0-9_.:/-]{1,160}')


def _directory(path, label):
    path = checked(path)
    if not path.is_dir():
        raise ValueError(f'existing {label} directory required')
    return path


def _separate(root, notes_root):
    for destination in (notes_root / '03_Media/Transcripts', notes_root / 'Conference'):
        if destination == root or root in destination.parents or destination in root.parents:
            raise ValueError('inbox and note destination must be separate trees')


def _settings(root, notes_root, model, backend, port, limit, timeout, min_age, interval_minutes):
    root = _directory(root, 'inbox')
    notes_root = _directory(notes_root, 'notes')
    _separate(root, notes_root)
    if backend not in LOCAL | {'auto'}:
        raise ValueError('scheduled inbox backend must be local')
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('scheduled inbox port must be 1..65535')
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('scheduled inbox limit must be 1..100')
    if (type(timeout) is not int or type(min_age) is not int or
            not 0 < timeout <= 86400 or not 0 <= min_age <= 86400):
        raise ValueError('invalid scheduled inbox timeout or quiet period')
    if not isinstance(model, str) or not MODEL.fullmatch(model):
        raise ValueError('invalid scheduled inbox model name')
    if type(interval_minutes) is not int or not 1 <= interval_minutes <= 1440:
        raise ValueError('scheduled inbox interval must be 1..1440 minutes')
    minimum_interval = math.ceil(((limit + 1) * timeout) / 60)
    if interval_minutes < minimum_interval:
        raise ValueError(f'scheduled inbox interval must allow at least {minimum_interval} minutes')
    return {
        'root': str(root), 'notes_root': str(notes_root), 'model': model, 'backend': backend,
        'port': port, 'limit': limit, 'timeout': timeout, 'min_age': min_age,
        'interval_minutes': interval_minutes,
    }


def _config_path(path, root):
    path = checked(path)
    if path.suffix.lower() != '.json' or not path.parent.is_dir():
        raise ValueError('scheduled inbox config must be a .json path in an existing directory')
    if path == root or root in path.parents:
        raise ValueError('scheduled inbox config must stay outside the inbox tree')
    return path


def _task_name(value):
    if not isinstance(value, str) or not re.fullmatch(r'[^\\/:*?"<>|\r\n]{1,128}', value):
        raise ValueError('scheduled inbox task name contains unsupported characters')
    return value


def _runtime_python():
    """Return the current interpreter after resolving its trusted launcher link."""
    return checked(Path(sys.executable).resolve())


def plan(root, notes_root, model, *, backend='auto', port=11434, limit=3, timeout=600,
         min_age=60, interval_minutes=120, config, task_name=DEFAULT_TASK_NAME):
    settings = _settings(root, notes_root, model, backend, port, limit, timeout, min_age, interval_minutes)
    config = _config_path(config, Path(settings['root']))
    task_name = _task_name(task_name)
    log = checked(config.with_suffix('.runs.jsonl'))
    runner = checked(REPO / 'scripts/process_inbox_schedule.py')
    controller = checked(REPO / 'scripts/process_inbox.py')
    return {
        'schema': SCHEMA,
        'owner': 'voidscape-process-inbox-schedule',
        'settings': settings,
        'task': {'name': task_name, 'runner': str(runner), 'controller': str(controller),
                 'python': str(_runtime_python()), 'config': str(config), 'log': str(log)},
    }


def _task_command(config):
    task = config['task']
    action = subprocess.list2cmdline([task['python'], task['runner'], '--run', '--config', task['config']])
    return ['schtasks.exe', '/Create', '/TN', task['name'], '/SC', 'MINUTE',
            '/MO', str(config['settings']['interval_minutes']), '/TR', action]


def preview(config):
    command = _task_command(config)
    return {
        'mode': 'preview', 'changes': False, 'config': config,
        'registration_command': subprocess.list2cmdline(command),
        'registration_notice': 'Review and run this command yourself to create the task. This helper never invokes it.',
    }


def write_config(config):
    path = checked(config['task']['config'])
    exclusive(path, encoded(config))
    return {'mode': 'written', 'changes': True, 'config': str(path),
            'registration_command': preview(config)['registration_command'],
            'registration_notice': 'No task was created. Review and run the command yourself if you want this schedule.'}


def _read_config(path):
    path = checked(path)
    with path.open('rb') as stream:
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError('scheduled inbox config exceeds limit')
    value = json.loads(raw)
    if set(value) != {'schema', 'owner', 'settings', 'task'} or value['schema'] != SCHEMA or value['owner'] != 'voidscape-process-inbox-schedule':
        raise ValueError('unrecognized scheduled inbox config')
    settings = value['settings']
    task = value['task']
    if set(settings) != {'root', 'notes_root', 'model', 'backend', 'port', 'limit', 'timeout', 'min_age', 'interval_minutes'}:
        raise ValueError('scheduled inbox settings do not match schema')
    expected = _settings(**settings)
    if expected != settings:
        raise ValueError('scheduled inbox settings changed')
    if set(task) != {'name', 'runner', 'controller', 'python', 'config', 'log'} or _task_name(task['name']) != task['name']:
        raise ValueError('scheduled inbox task does not match schema')
    root = Path(settings['root'])
    config = _config_path(task['config'], root)
    if (config != path or checked(task['runner']) != checked(REPO / 'scripts/process_inbox_schedule.py') or
            checked(task['controller']) != checked(REPO / 'scripts/process_inbox.py') or
            checked(task['python']) != _runtime_python()):
        raise ValueError('scheduled inbox executable paths changed')
    log = checked(task['log'])
    if log != checked(config.with_suffix('.runs.jsonl')) or log.parent != config.parent:
        raise ValueError('scheduled inbox log path changed')
    return value


def _append_summary(path, summary):
    path = checked(path)
    with path.open('ab') as stream:
        stream.write((json.dumps(summary, ensure_ascii=False, sort_keys=True) + '\n').encode('utf-8'))
        stream.flush()
        os.fsync(stream.fileno())


def run(config_path):
    config = _read_config(config_path)
    settings, task = config['settings'], config['task']
    command = [task['python'], task['controller'], '--root', settings['root'], '--notes-root', settings['notes_root'],
               '--model', settings['model'], '--backend', settings['backend'], '--port', str(settings['port']),
               '--limit', str(settings['limit']), '--timeout', str(settings['timeout']), '--min-age', str(settings['min_age']), '--apply']
    summary = {'schema': SCHEMA, 'at': datetime.now(timezone.utc).isoformat(), 'status': 'failed',
               'processed': 0, 'skipped': 0, 'failed': 0, 'deferred': 0}
    try:
        completed = subprocess.run(command, cwd=REPO, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL, text=True, encoding='utf-8', timeout=settings['timeout'] * (settings['limit'] + 1) + 60)
        response = json.loads(completed.stdout)
        data = response['data']
        if not isinstance(response, dict) or response.get('ok') is not True or not isinstance(data, dict):
            raise ValueError('controller did not return a valid success envelope')
        if data.get('status') == 'busy':
            summary.update(status='busy')
        else:
            for field in ('processed', 'skipped', 'failed', 'deferred'):
                value = data.get(field)
                if type(value) is not int or value < 0:
                    raise ValueError('controller summary is invalid')
                summary[field] = value
            summary['status'] = 'completed' if completed.returncode == 0 and summary['failed'] == 0 else 'failed'
    except (TypeError, ValueError, KeyError, json.JSONDecodeError, subprocess.TimeoutExpired):
        pass
    _append_summary(task['log'], summary)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root')
    parser.add_argument('--notes-root')
    parser.add_argument('--model')
    parser.add_argument('--backend', choices=['auto', *sorted(LOCAL)], default='auto')
    parser.add_argument('--port', type=int, default=11434)
    parser.add_argument('--limit', type=int, default=3)
    parser.add_argument('--timeout', type=int, default=600)
    parser.add_argument('--min-age', type=int, default=60)
    parser.add_argument('--interval-minutes', type=int, default=120)
    parser.add_argument('--config')
    parser.add_argument('--task-name', default=DEFAULT_TASK_NAME)
    parser.add_argument('--write-config', action='store_true')
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.run:
            if any(value is not None for value in (args.root, args.notes_root, args.model)) or args.write_config or not args.config:
                raise ValueError('scheduled inbox runner requires only --config')
            result = run(args.config)
            print(json.dumps({'ok': result['status'] != 'failed', 'data': result, 'error': None if result['status'] != 'failed' else 'Scheduled inbox run failed; review retained local evidence.'}))
            return 0 if result['status'] != 'failed' else 6
        if not all((args.root, args.notes_root, args.model, args.config)):
            raise ValueError('root, notes root, model and config are required')
        config = plan(args.root, args.notes_root, args.model, backend=args.backend, port=args.port,
                      limit=args.limit, timeout=args.timeout, min_age=args.min_age,
                      interval_minutes=args.interval_minutes, config=args.config, task_name=args.task_name)
        result = write_config(config) if args.write_config else preview(config)
        print(json.dumps({'ok': True, 'data': result, 'error': None}))
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError, subprocess.TimeoutExpired):
        print(json.dumps({'ok': False, 'data': None, 'error': 'Scheduled inbox configuration failed; no task was created.'}))
        return 6


if __name__ == '__main__':
    raise SystemExit(main())
