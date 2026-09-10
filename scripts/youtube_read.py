"""Bind a selected public YouTube capture to governed local media evidence."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

from process_deadline import run as run_worker
from triage_store import checked, encoded, exclusive, file_digest, locked
from youtube_ingest_helper import read_json, verify as verify_capture
from youtube_source import selection


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skill/scripts'))
from video import redact_remote_url

LOCAL = {'captions', 'faster-whisper', 'whisper-cpp'}


def matches_input(data, url):
    displayed, redacted = redact_remote_url(url)
    return data.get('input') == displayed and data.get('input_redacted') is redacted


def invoke(command, url, work, *options):
    log = checked(work / f'{command}-{uuid.uuid4().hex}.json')
    errors = log.with_suffix('.stderr')
    with log.open('xb') as stdout, errors.open('xb') as stderr:
        result = subprocess.run([sys.executable, '-B', '-m', 'skill.scripts.voidscape', command,
                                 url, *options, '--json'], cwd=ROOT, stdin=subprocess.DEVNULL,
                                stdout=stdout, stderr=stderr,
                                env={**os.environ, 'READ_VIDEO_YTDLP_COOKIES': ''})
    if result.returncode:
        raise ValueError('public video reader failed; inspect retained local diagnostics')
    data = read_json(log)
    if not isinstance(data, dict) or any(field in data for field in ('ok', 'data', 'error')):
        raise ValueError('unexpected guided reader contract')
    return data


def verify_read(work, key):
    work = checked(work)
    ready = read_json(work / 'ready.json')
    if (ready['schema'] != 1 or ready['key'] != key or selection(ready['url'])['key'] != key or
            ready['info'].get('source') != 'url' or ready['info'].get('youtube_id') != key[8:] or
            not matches_input(ready['info'], ready['url']) or
            ready['backend'] not in (LOCAL if ready['tier'] in {'both', 'audio'} else {'none'}) or
            ready['tier'] not in {'both', 'audio', 'visual'} or ready['content_trust'] != 'untrusted'):
        raise ValueError('read provenance mismatch')
    bundle = checked(work / 'evidence')
    artifacts = []
    if not isinstance(ready['artifacts'], list) or not 1 <= len(ready['artifacts']) <= 512:
        raise ValueError('invalid read artifact bounds')
    for artifact in ready['artifacts']:
        path = checked(bundle / artifact['path'])
        path.relative_to(bundle)
        if file_digest(path) != artifact['sha256']:
            raise ValueError('read evidence changed')
        artifacts.append(path)
    manifest_path = checked(bundle / 'manifest.json')
    if manifest_path not in artifacts:
        raise ValueError('read manifest is not retained')
    manifest = read_json(manifest_path)
    if (manifest.get('status') != 'complete' or manifest.get('backend') != ready['backend'] or
            checked(manifest['workdir']) != bundle):
        raise ValueError('complete matching read manifest required')
    for frame in manifest.get('frames', []):
        if checked(frame['file']) not in artifacts:
            raise ValueError('frame is not retained')
    if manifest.get('transcript') and checked(manifest['transcript']) not in artifacts:
        raise ValueError('transcript is not retained')
    if not manifest.get('transcript') and not manifest.get('frames'):
        raise ValueError('read produced no usable evidence')
    return ready, manifest, [work / 'ready.json', *artifacts]


def prepare(root, key, work, *, backend='auto', tier='both', reader=invoke):
    """Worker runs all three reader stages; no gate can select cloud or a new model."""
    entry = verify_capture(root, key)
    work = checked(work)
    if backend not in LOCAL | {'auto'} or tier not in {'both', 'audio', 'visual'}:
        raise ValueError('unsupported public read mode')
    if (work / 'ready.json').exists():
        ready, manifest, artifacts = verify_read(work, key)
        if ready['requested_backend'] != backend or ready['tier'] != tier:
            raise ValueError('retained read requested with different settings')
        return {'status': 'ready', 'key': key, 'ready': str(work / 'ready.json'), 'duplicate': True}
    info = reader('inspect', entry['url'], work)
    if info.get('source') != 'url' or info.get('youtube_id') != key[8:] or not matches_input(info, entry['url']):
        raise ValueError('reader inspected a different source')
    selected = ('captions' if info.get('captions_available') is True else 'faster-whisper') if backend == 'auto' else backend
    if tier == 'visual':
        selected = 'captions'  # Ignored by the visual reader; never requests transcription.
    expected = 'none' if tier == 'visual' else selected
    options = ('--tier', tier, '--backend', selected)
    preview = reader('preview', entry['url'], work, *options)
    if (preview.get('backend') != expected or not matches_input(preview, entry['url']) or preview.get('free') is not True or
            any(preview.get(flag) is not False for flag in ('requires_cloud_approval', 'needs_model_download', 'needs_install'))):
        raise ValueError('read requires explicit safe gates and an available local backend')
    bundle = checked(work / 'evidence')
    result = reader('read', entry['url'], work, *options, '--workdir', str(bundle))
    if result.get('status') != 'complete' or result.get('backend') != expected:
        raise ValueError('reader did not complete the selected backend')
    artifacts = []
    for path in bundle.rglob('*'):
        if path.is_file():
            path = checked(path)
            path.relative_to(bundle)
            artifacts.append({'path': path.relative_to(bundle).as_posix(), 'sha256': file_digest(path)})
            if len(artifacts) > 512:
                raise ValueError('read produced too many artifacts')
    ready = {'schema': 1, 'key': key, 'url': entry['url'], 'info': info, 'requested_backend': backend,
             'backend': expected, 'tier': tier, 'artifacts': artifacts, 'content_trust': 'untrusted'}
    if len(encoded(ready)) > 1024 * 1024:
        raise ValueError('read receipt exceeds limit')
    exclusive(work / 'ready.json', encoded(ready))
    verify_read(work, key)
    return {'status': 'ready', 'key': key, 'ready': str(work / 'ready.json'), 'duplicate': False}


def read(root, key, work, *, allow_read=False, backend='auto', tier='both', timeout=1800):
    if not allow_read:
        raise PermissionError('public media read requires explicit --allow-read')
    verify_capture(root, key)
    if backend not in LOCAL | {'auto'} or tier not in {'both', 'audio', 'visual'} or not 0 < timeout <= 7200:
        raise ValueError('invalid read options')
    work = checked(work)
    work.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, '-B', str(Path(__file__).resolve()), str(checked(root)), key,
               str(work), '--worker', '--backend', backend, '--tier', tier]
    with locked(work):
        run_worker(command, timeout=timeout, log=work / f'worker-{uuid.uuid4().hex}.log', cwd=ROOT)
        verify_read(work, key)
    return {'status': 'ready', 'key': key, 'ready': str(work / 'ready.json'), 'source_action_authorized': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ('root', 'key', 'work'):
        parser.add_argument(field)
    parser.add_argument('--backend', choices=['auto', *sorted(LOCAL)], default='auto')
    parser.add_argument('--tier', choices=['both', 'audio', 'visual'], default='both')
    parser.add_argument('--allow-read', action='store_true')
    parser.add_argument('--timeout', type=int, default=1800)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = vars(parser.parse_args(argv))
    worker = args.pop('worker')
    try:
        if worker:
            if sys.stdin.readline() != 'GO\n':
                raise ValueError('owned worker handshake required')
            args.pop('allow_read')
            args.pop('timeout')
            result = prepare(**args)
        else:
            result = read(**args)
        print(json.dumps({'ok': True, 'data': result, 'error': None}))
        return 0
    except (OSError, ValueError, KeyError, TypeError, RuntimeError):
        print(json.dumps({'ok': False, 'data': None, 'error': {'code': 'youtube_read_failed',
                          'message': 'YouTube read failed; preserve evidence and inspect locally'}}))
        return 6


if __name__ == '__main__':
    raise SystemExit(main())
