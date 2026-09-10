"""Read one retained RSS article through the governed public article reader."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import uuid

from process_deadline import run as run_worker
from rss_capture_helper import verify as verify_capture
from rss_resource import select
from triage_store import checked, digest, encoded, exclusive, file_digest, locked
from youtube_ingest_helper import read_json
from youtube_read import ROOT, invoke


def verify_read(root, key, work, *, candidate=None):
    """Recheck capture identity, immutable files and the actual article manifest."""
    selected = select(root, key)
    capture = verify_capture(root, key[4:])
    work = checked(work)
    ready = read_json(work / 'ready.json') if candidate is None else candidate
    if (ready.get('schema') != 1 or ready.get('selection') != selected or
            ready.get('capture_sha256') != digest(encoded(capture)) or
            ready.get('content_trust') != 'untrusted'):
        raise ValueError('article read provenance mismatch')
    bundle = checked(work / 'evidence')
    artifacts = ready.get('artifacts')
    if not isinstance(artifacts, list) or not 1 <= len(artifacts) <= 16:
        raise ValueError('invalid article artifact bounds')
    paths = []
    for item in artifacts:
        if not isinstance(item, dict) or not isinstance(item.get('path'), str):
            raise ValueError('invalid article artifact')
        relative = Path(item['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('article artifact must be relative and confined')
        path = checked(bundle / relative)
        path.relative_to(bundle)
        if path in paths or file_digest(path) != item.get('sha256'):
            raise ValueError('article evidence changed or duplicated')
        paths.append(path)
    manifest_path = bundle / 'manifest.json'
    if manifest_path not in paths:
        raise ValueError('article manifest not retained')
    manifest = read_json(manifest_path)
    if (manifest.get('status') != 'complete' or manifest.get('kind') != 'article' or
            manifest.get('entry_kind') != 'article' or manifest.get('source') != 'url' or
            manifest.get('input') != selected['url'] or manifest.get('input_redacted') is not False or
            checked(manifest['workdir']) != bundle or manifest.get('item_count') != 1 or
            not isinstance(manifest.get('content_trust'), dict) or
            manifest['content_trust'].get('source_content') != 'untrusted'):
        raise ValueError('complete matching public article manifest required')
    entries = manifest.get('entries')
    if (not isinstance(entries, list) or len(entries) != 1 or
            not isinstance(entries[0], dict) or entries[0].get('citation') != '[article 1]' or
            checked(entries[0]['file']) not in paths or
            type(entries[0].get('word_count')) is not int or entries[0]['word_count'] < 1):
        raise ValueError('usable retained article evidence required')
    return ready, manifest, [work / 'ready.json', *paths]


def prepare(root, key, work, *, reader=invoke):
    """Owned worker: inspect and preview before the explicitly authorized fetch."""
    selected = select(root, key)
    capture_hash = digest(encoded(verify_capture(root, key[4:])))
    work = checked(work)
    if (work / 'ready.json').exists():
        verify_read(root, key, work)
        return {'status': 'ready', 'duplicate': True, 'key': key}
    options = ('--reader', 'article')
    info = reader('inspect', selected['url'], work, *options)
    if (info.get('input') != selected['url'] or info.get('input_redacted') is not False or
            info.get('source') != 'url' or info.get('kind') != 'article_url'):
        raise ValueError('article inspection source mismatch')
    preview = reader('preview', selected['url'], work, *options)
    if (preview.get('input') != selected['url'] or preview.get('input_redacted') is not False or
            preview.get('requires_fetch_approval') is not True or
            preview.get('requires_cloud_approval') is not True or
            preview.get('requires_browser_auth') is not False or
            preview.get('gate') != {'type': 'cloud_approval', 'backend': 'article_fetch'} or
            preview.get('needs_model_download') is not False or preview.get('needs_install') is not False):
        raise ValueError('unexpected article consent gates')
    bundle = checked(work / 'evidence')
    # Guided CLI names the article-fetch gate --allow-cloud; forcing the article
    # reader and checking article_fetch above keeps this distinct from AI transfer.
    result = reader('read', selected['url'], work, *options, '--allow-cloud', '--workdir', str(bundle))
    if result.get('status') != 'complete' or result.get('kind') != 'article':
        raise ValueError('article reader did not complete a single article')
    artifacts = []
    for path in bundle.rglob('*'):
        if path.is_file():
            path = checked(path)
            artifacts.append({'path': path.relative_to(bundle).as_posix(), 'sha256': file_digest(path)})
            if len(artifacts) > 16:
                raise ValueError('too many article artifacts')
    ready = {'schema': 1, 'selection': selected, 'capture_sha256': capture_hash,
             'artifacts': artifacts, 'content_trust': 'untrusted'}
    verify_read(root, key, work, candidate=ready)
    exclusive(work / 'ready.json', encoded(ready))
    verify_read(root, key, work)
    return {'status': 'ready', 'duplicate': False, 'key': key}


def read(root, key, work, *, allow_fetch=False, timeout=180):
    if not allow_fetch:
        raise PermissionError('article fetch requires explicit --allow-fetch')
    select(root, key)
    if type(timeout) is not int or not 0 < timeout <= 600:
        raise ValueError('timeout must be between 1 and 600 seconds')
    work = checked(work)
    work.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, '-B', str(Path(__file__).resolve()), str(checked(root)),
               key, str(work), '--worker']
    with locked(work):
        run_worker(command, timeout=timeout, log=work / f'worker-{uuid.uuid4().hex}.log', cwd=ROOT)
        verify_read(root, key, work)
    return {'status': 'ready', 'key': key, 'ready': str(work / 'ready.json'),
            'source_action_authorized': False, 'coverage': 'fetched_public_text_only'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'key', 'work'):
        parser.add_argument(name)
    parser.add_argument('--allow-fetch', action='store_true')
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = vars(parser.parse_args(argv))
    try:
        if args.pop('worker'):
            if sys.stdin.readline() != 'GO\n':
                raise ValueError('owned worker handshake required')
            args.pop('allow_fetch')
            args.pop('timeout')
            result = prepare(**args)
        else:
            result = read(**args)
        print(json.dumps({'ok': True, 'data': result, 'error': None}))
        return 0
    except (OSError, ValueError, KeyError, TypeError, RuntimeError):
        print(json.dumps({'ok': False, 'data': None, 'error': {'code': 'rss_read_failed',
                          'message': 'Article read failed; preserve evidence and inspect locally'}}))
        return 6


if __name__ == '__main__':
    raise SystemExit(main())
