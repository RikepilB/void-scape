"""Bind a retained RSS enclosure to local transcript/frame evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import uuid

from process_deadline import run as run_worker
from rss_download import ROOT, verify_download
from triage_store import checked, digest, encoded, exclusive, file_digest, locked
from youtube_ingest_helper import read_json
from youtube_read import invoke

LOCAL = {'faster-whisper', 'whisper-cpp'}


def verify_read(root, key, work, *, candidate=None):
    work = checked(work)
    ready = read_json(work / 'ready.json') if candidate is None else candidate
    if (not isinstance(ready, dict) or ready.get('schema') != 1 or ready.get('kind') != 'rss_media' or
            ready.get('key') != key or ready.get('content_trust') != 'untrusted' or
            ready.get('requested_backend') not in LOCAL or ready.get('tier') not in {'audio', 'both', 'visual'}):
        raise ValueError('invalid enclosure read receipt')
    download_root = checked(ready['download_root'])
    record, originals = verify_download(root, key, download_root, ready['enclosure'])
    if ready.get('download_sha256') != digest(encoded(record)):
        raise ValueError('enclosure read download binding changed')
    expected = 'none' if ready['tier'] == 'visual' else ready['requested_backend']
    info = ready.get('info')
    if (not isinstance(info, dict) or info.get('source') != 'local' or
            checked(info['input']) != originals[1] or info.get('sidecar_transcript') is not None):
        raise ValueError('enclosure reader inspected a different input')
    bundle = checked(work / 'evidence')
    artifacts = ready.get('artifacts')
    if not isinstance(artifacts, list) or not 1 <= len(artifacts) <= 512:
        raise ValueError('invalid media artifact bounds')
    paths = []
    for item in artifacts:
        if not isinstance(item, dict) or not isinstance(item.get('path'), str):
            raise ValueError('invalid media artifact')
        relative = Path(item['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('media artifact must be relative')
        path = checked(bundle / relative)
        path.relative_to(bundle)
        if path in paths or file_digest(path) != item.get('sha256'):
            raise ValueError('media evidence changed or duplicated')
        paths.append(path)
    if bundle / 'manifest.json' not in paths:
        raise ValueError('media manifest not retained')
    manifest = read_json(bundle / 'manifest.json')
    if (not isinstance(manifest, dict) or manifest.get('status') != 'complete' or
            manifest.get('backend') != expected or manifest.get('tier') != ready['tier'] or
            checked(manifest['workdir']) != bundle or
            not isinstance(manifest.get('content_trust'), dict) or
            manifest['content_trust'].get('source_content') != 'untrusted'):
        raise ValueError('complete matching media manifest required')
    frames = manifest.get('frames')
    if not isinstance(frames, list) or len(frames) > 100:
        raise ValueError('invalid frame list')
    for frame in frames:
        if not isinstance(frame, dict) or checked(frame['file']) not in paths:
            raise ValueError('frame is not retained')
    transcript = manifest.get('transcript')
    if transcript and checked(transcript) not in paths:
        raise ValueError('transcript is not retained')
    if ready['tier'] in {'audio', 'both'} and not transcript:
        raise ValueError('selected audio tier requires retained transcript')
    if transcript:
        with checked(transcript).open('rb') as stream:
            raw = stream.read(16 * 1024 * 1024 + 1)
        if len(raw) > 16 * 1024 * 1024 or not re.search(
                r'^\[\d{2,}:[0-5]\d(?::[0-5]\d)?\][ \t]+\S', raw.decode('utf-8'), re.MULTILINE):
            raise ValueError('usable timestamped transcript required; no speech is not analyzed content')
    if ready['tier'] in {'visual', 'both'} and not frames:
        raise ValueError('selected visual tier requires retained frames')
    return ready, manifest, [download_root / 'download.json', *originals, work / 'ready.json', *paths]


def prepare(root, key, download_root, work, *, enclosure=1, backend='faster-whisper', tier=None, reader=invoke):
    record, originals = verify_download(root, key, download_root, enclosure)
    tier = tier or record['selection']['tier']
    if backend not in LOCAL or tier not in {'audio', 'both', 'visual'}:
        raise ValueError('unsupported local enclosure read mode')
    work = checked(work)
    if (work / 'ready.json').exists():
        ready, _, _ = verify_read(root, key, work)
        if (ready['enclosure'] != enclosure or ready['requested_backend'] != backend or
                ready['tier'] != tier or checked(ready['download_root']) != checked(download_root)):
            raise ValueError('retained media requested with different settings')
        return {'status': 'ready', 'duplicate': True}
    media = str(originals[1])
    options = ('--reader', 'video', '--tier', tier, '--backend', backend, '--transcribe-mode', 'fast')
    info = reader('inspect', media, work, '--reader', 'video')
    if (info.get('source') != 'local' or checked(info['input']) != originals[1] or
            info.get('sidecar_transcript') is not None):
        raise ValueError('enclosure source mismatch or unverified transcript sidecar')
    expected = 'none' if tier == 'visual' else backend
    preview = reader('preview', media, work, *options)
    if (preview.get('source') != 'local' or checked(preview['input']) != originals[1] or
            preview.get('backend') != expected or preview.get('tier') != tier or
            preview.get('free') is not True or preview.get('sidecar_transcript') is not None or
            any(preview.get(flag) is not False for flag in ('requires_cloud_approval', 'needs_model_download', 'needs_install'))):
        raise ValueError('enclosure read requires an available approved local backend')
    bundle = checked(work / 'evidence')
    result = reader('read', media, work, *options, '--workdir', str(bundle))
    if result.get('status') != 'complete' or result.get('backend') != expected:
        raise ValueError('local enclosure reader did not complete')
    artifacts = []
    for path in bundle.rglob('*'):
        if path.is_file():
            path = checked(path)
            artifacts.append({'path': path.relative_to(bundle).as_posix(), 'sha256': file_digest(path)})
            if len(artifacts) > 512:
                raise ValueError('too many media artifacts')
    ready = {'schema': 1, 'kind': 'rss_media', 'key': key, 'enclosure': enclosure,
             'download_root': str(checked(download_root)), 'download_sha256': digest(encoded(record)),
             'info': info, 'requested_backend': backend, 'tier': tier,
             'artifacts': artifacts, 'content_trust': 'untrusted'}
    verify_read(root, key, work, candidate=ready)
    exclusive(work / 'ready.json', encoded(ready))
    verify_read(root, key, work)
    return {'status': 'ready', 'duplicate': False}


def read(root, key, download_root, work, *, enclosure=1, backend='faster-whisper', tier=None,
         timeout=1800, allow_read=False):
    if not allow_read:
        raise PermissionError('local enclosure processing requires explicit --allow-read')
    record, _ = verify_download(root, key, download_root, enclosure)
    tier = tier or record['selection']['tier']
    if (backend not in LOCAL or tier not in {'audio', 'both', 'visual'} or
            type(timeout) is not int or not 1 <= timeout <= 7200):
        raise ValueError('invalid enclosure read settings')
    work = checked(work)
    work.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, '-B', str(Path(__file__).resolve()), str(checked(root)), key,
               str(checked(download_root)), str(work), '--worker', '--enclosure', str(enclosure),
               '--backend', backend, '--tier', tier]
    with locked(work):
        run_worker(command, timeout=timeout, log=work / f'worker-{uuid.uuid4().hex}.log', cwd=ROOT)
        verify_read(root, key, work)
    return {'status': 'ready', 'key': key, 'ready': str(work / 'ready.json'),
            'source_action_authorized': False, 'timeline': 'retained normalized enclosure'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'key', 'download_root', 'work'):
        parser.add_argument(name)
    parser.add_argument('--enclosure', type=int, default=1)
    parser.add_argument('--backend', choices=sorted(LOCAL), default='faster-whisper')
    parser.add_argument('--tier', choices=['audio', 'both', 'visual'])
    parser.add_argument('--timeout', type=int, default=1800)
    parser.add_argument('--allow-read', action='store_true')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = vars(parser.parse_args(argv))
    try:
        if args.pop('worker'):
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
        print(json.dumps({'ok': False, 'data': None, 'error': {'code': 'rss_media_failed',
                          'message': 'Enclosure reading failed; preserve evidence and inspect locally'}}))
        return 6


if __name__ == '__main__':
    raise SystemExit(main())
