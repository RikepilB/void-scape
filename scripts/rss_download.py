"""Bounded anonymous enclosure acquisition and descriptor-only media remuxing."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request
import uuid

from process_deadline import run as run_worker, ProcessDeadlineError
from rss_capture_helper import article, verify as verify_capture
from rss_resource import select
from triage_store import checked, digest, encoded, exclusive, file_digest, locked
from youtube_ingest_helper import read_json

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BYTES = 128 * 1024 * 1024
MAX_BYTES = 512 * 1024 * 1024
FORMATS = 'aac,avi,flac,matroska,webm,mov,mp3,mpeg,mpegts,ogg,wav'


class AccessDenied(PermissionError):
    def __init__(self, status):
        self.status = status
        super().__init__('public enclosure access denied; no authenticated fallback')


def ffmpeg_ready():
    """Check descriptor support before acquiring any remote bytes."""
    if not shutil.which('ffmpeg'):
        return False
    try:
        result = subprocess.run(['ffmpeg', '-hide_banner', '-protocols'], capture_output=True,
                                text=True, timeout=5,
                                env={k: v for k, v in os.environ.items() if k.upper() != 'FFREPORT'},
                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        return result.returncode == 0 and result.stdout.split().count('fd') >= 2
    except (OSError, subprocess.TimeoutExpired):
        return False


def limits(max_bytes, timeout):
    if (type(max_bytes) is not int or not 1 <= max_bytes <= MAX_BYTES or
            type(timeout) is not int or not 1 <= timeout <= 1800):
        raise ValueError('invalid enclosure byte/deadline bounds')


def fetch(url, target, max_bytes, *, opener=article._open_url):
    """Each hop uses the pinned public transport; no proxy, cookies or credentials."""
    limits(max_bytes, 300)
    current = url
    for hop in range(article.MAX_REDIRECTS + 1):
        request = Request(current, headers={'Accept': 'audio/*, video/*',
                          'User-Agent': 'Voidscape/1.0 enclosure-reader'})
        try:
            response = opener(request, 20.0)
        except HTTPError as error:
            if error.code not in {301, 302, 303, 307, 308}:
                if error.code in {401, 403}:
                    raise AccessDenied(error.code) from None
                raise ValueError('enclosure HTTP request failed') from None
            location = error.headers.get('Location')
            if not location or hop == article.MAX_REDIRECTS:
                raise ValueError('enclosure redirect missing or limit exceeded') from None
            next_url = urljoin(current, location)
            if urlsplit(current).scheme.lower() == 'https' and urlsplit(next_url).scheme.lower() == 'http':
                raise ValueError('enclosure HTTPS downgrade refused') from None
            current = next_url
            continue
        except URLError:
            raise ValueError('enclosure network request failed') from None
        with response:
            mime = response.headers.get('Content-Type', '').split(';', 1)[0].strip().lower()
            if not re.fullmatch(r'(audio|video)/[a-z0-9!#$&^_.+-]+', mime):
                raise ValueError('enclosure response is not explicit audio/video media')
            if response.headers.get('Content-Encoding', '').strip().lower() not in {'', 'identity'}:
                raise ValueError('compressed HTTP enclosure response is unsupported')
            length = response.headers.get('Content-Length')
            if length is not None and (not re.fullmatch(r'[0-9]{1,12}', length) or int(length) > max_bytes):
                raise ValueError('enclosure declared length invalid or over budget')
            total = 0
            with checked(target).open('xb') as output:
                while True:
                    chunk = response.read(min(65536, max_bytes + 1 - total))
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError('enclosure exceeds byte budget')
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            if not total or (length is not None and total != int(length)):
                raise ValueError('empty or truncated enclosure response')
            # Redirect destinations can contain expiring secrets. Retain only the
            # validated initial selection and hop count, not the redirected URL.
            return {'bytes': total, 'response_type': mime, 'redirects': hop}
    raise ValueError('enclosure redirect limit exceeded')


def remux(source, target, max_bytes):
    """Read only descriptor zero; do not let the demuxer open paths or URLs."""
    ceiling = max_bytes * 2 + 1024 * 1024
    command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin',
               '-protocol_whitelist', 'fd', '-format_whitelist', FORMATS, '-i', 'fd:',
               '-map', '0:v:0?', '-map', '0:a:0?', '-map_metadata', '-1', '-map_chapters', '-1',
               '-copyts', '-start_at_zero', '-c', 'copy', '-fs', str(ceiling), '-f', 'matroska', 'fd:']
    log = checked(Path(target).with_suffix('.stderr'))
    with checked(source).open('rb') as incoming, checked(target).open('xb') as outgoing, log.open('xb') as errors:
        result = subprocess.run(command, stdin=incoming, stdout=outgoing, stderr=errors,
                                env={k: v for k, v in os.environ.items() if k.upper() != 'FFREPORT'},
                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        outgoing.flush()
        os.fsync(outgoing.fileno())
    size = checked(target).stat().st_size
    if result.returncode or not 0 < size < ceiling:
        raise ValueError('bounded descriptor-only remux failed; preserve source and diagnostics')


def verify_download(root, key, work, enclosure=1, *, candidate=None):
    selected = select(root, key, 'enclosure', enclosure)
    work = checked(work)
    record = read_json(work / 'download.json') if candidate is None else candidate
    if (not isinstance(record, dict) or record.get('schema') != 1 or record.get('selection') != selected or
            record.get('capture_sha256') != digest(encoded(verify_capture(root, key[4:]))) or
            record.get('content_trust') != 'untrusted' or record.get('decode_policy') != 'descriptor-only-v1'):
        raise ValueError('enclosure download provenance mismatch')
    limits(record.get('max_bytes'), record.get('timeout'))
    expected = ['source.bin', 'media.mkv']
    artifacts = record.get('artifacts')
    if not isinstance(artifacts, list) or len(artifacts) != 2:
        raise ValueError('enclosure requires original and remuxed artifacts')
    paths = []
    for item, name in zip(artifacts, expected):
        if not isinstance(item, dict) or item.get('path') != name:
            raise ValueError('unexpected enclosure artifact')
        path = checked(work / name)
        size = path.stat().st_size
        bound = record['max_bytes'] if name == 'source.bin' else record['max_bytes'] * 2 + 1024 * 1024 - 1
        if not 0 < size <= bound:
            raise ValueError('enclosure artifact size outside bounds')
        if file_digest(path) != item.get('sha256'):
            raise ValueError('enclosure evidence changed')
        paths.append(path)
    transfer = record.get('transfer')
    if (not isinstance(transfer, dict) or type(transfer.get('bytes')) is not int or
            transfer['bytes'] != paths[0].stat().st_size or
            not isinstance(transfer.get('response_type'), str) or
            not re.fullmatch(r'(audio|video)/[a-z0-9!#$&^_.+-]+', transfer['response_type']) or
            type(transfer.get('redirects')) is not int or not 0 <= transfer['redirects'] <= article.MAX_REDIRECTS):
        raise ValueError('invalid enclosure transfer receipt')
    return record, paths


def prepare(root, key, work, *, enclosure=1, max_bytes=DEFAULT_BYTES, timeout=300,
            fetcher=fetch, normalizer=remux):
    limits(max_bytes, timeout)
    selected = select(root, key, 'enclosure', enclosure)
    capture_hash = digest(encoded(verify_capture(root, key[4:])))
    work = checked(work)
    if (work / 'download.json').exists():
        record, _ = verify_download(root, key, work, enclosure)
        if record['max_bytes'] != max_bytes or record['timeout'] != timeout:
            raise ValueError('retained enclosure requested with different bounds')
        return {'status': 'captured', 'duplicate': True}
    if any((work / name).exists() for name in ('source.bin', 'media.mkv', 'media.stderr')):
        raise ValueError('incomplete enclosure artifacts exist; preserve and choose a fresh work directory')
    source, media = work / 'source.bin', work / 'media.mkv'
    transfer = fetcher(selected['url'], source, max_bytes)
    normalizer(source, media, max_bytes)
    record = {'schema': 1, 'selection': selected, 'capture_sha256': capture_hash,
              'max_bytes': max_bytes, 'timeout': timeout, 'transfer': transfer,
              'decode_policy': 'descriptor-only-v1', 'content_trust': 'untrusted',
              'timeline': 'remuxed presentation timestamps shifted to start at zero',
              'artifacts': [{'path': p.name, 'sha256': file_digest(p)} for p in (source, media)]}
    verify_download(root, key, work, enclosure, candidate=record)
    exclusive(work / 'download.json', encoded(record))
    verify_download(root, key, work, enclosure)
    return {'status': 'captured', 'duplicate': False}


def capture(root, key, work, *, enclosure=1, max_bytes=DEFAULT_BYTES, timeout=300, allow_fetch=False):
    limits(max_bytes, timeout)
    selected = select(root, key, 'enclosure', enclosure)
    preview = {'status': 'preview', 'selection': selected, 'max_bytes': max_bytes,
               'timeout': timeout, 'requires_fetch_approval': True, 'transcribes': False,
               'requires_ffmpeg': not ffmpeg_ready(), 'source_action_authorized': False}
    if not allow_fetch:
        return preview
    if preview['requires_ffmpeg']:
        raise ValueError('FFmpeg with fd input/output support is required; no automatic installation')
    work = checked(work)
    work.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, '-B', str(Path(__file__).resolve()), str(checked(root)), key, str(work),
               '--worker', '--enclosure', str(enclosure), '--max-bytes', str(max_bytes), '--timeout', str(timeout)]
    with locked(work):
        log = work / f'worker-{uuid.uuid4().hex}.log'
        try:
            run_worker(command, timeout=timeout, log=log, cwd=ROOT)
        except ProcessDeadlineError:
            try:
                failure = read_json(log)
            except (OSError, ValueError):
                failure = None
            if isinstance(failure, dict) and isinstance(failure.get('error'), dict):
                error = failure['error']
                if error.get('code') == 'rss_access_denied' and error.get('http_status') in {401, 403}:
                    raise AccessDenied(error['http_status']) from None
            raise
        verify_download(root, key, work, enclosure)
    return {'status': 'captured', 'download': str(work / 'download.json'), 'media': str(work / 'media.mkv'),
            'analyzed': False, 'source_action_authorized': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'key', 'work'):
        parser.add_argument(name)
    parser.add_argument('--enclosure', type=int, default=1)
    parser.add_argument('--max-bytes', type=int, default=DEFAULT_BYTES)
    parser.add_argument('--timeout', type=int, default=300)
    parser.add_argument('--allow-fetch', action='store_true')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = vars(parser.parse_args(argv))
    try:
        if args.pop('worker'):
            if sys.stdin.readline() != 'GO\n':
                raise ValueError('owned worker handshake required')
            args.pop('allow_fetch')
            result = prepare(**args)
        else:
            result = capture(**args)
        print(json.dumps({'ok': True, 'data': result, 'error': None}))
        return 0
    except AccessDenied as error:
        print(json.dumps({'ok': False, 'data': None, 'error': {'code': 'rss_access_denied',
                          'http_status': error.status,
                          'message': 'Public enclosure access denied; record the observed limitation without bypassing access'}}))
        return 6
    except (OSError, ValueError, KeyError, TypeError, RuntimeError):
        print(json.dumps({'ok': False, 'data': None, 'error': {'code': 'rss_download_failed',
                          'message': 'Enclosure acquisition failed; preserve artifacts and inspect locally'}}))
        return 6


if __name__ == '__main__':
    raise SystemExit(main())
