"""Bounded public metadata discovery, separate from OAuth queue operations."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading

from youtube_source import VIDEO_ID, selection


MAX_OUTPUT = 8 * 1024 * 1024


class FetchApprovalRequired(PermissionError):
    """Public metadata fetching was not authorized by the caller."""


def command(url, start, limit):
    return [sys.executable, '-I', '-B', '-m', 'yt_dlp', '--ignore-config', '--no-plugin-dirs',
            '--no-js-runtimes', '--no-remote-components', '--no-cache-dir', '--no-mark-watched',
            '--simulate', '--flat-playlist', '--dump-single-json', '--abort-on-error',
            '--socket-timeout', '15', '--extractor-retries', '0', '--retries', '0',
            '--playlist-items', f'{start}:{start + limit - 1}', '--', url]


def run(args, *, timeout=60, max_output=MAX_OUTPUT):
    """Drain bounded pipes and terminate on deadline or excess output; never echo logs."""
    if not 0 < timeout <= 120 or not 1 <= max_output <= MAX_OUTPUT:
        raise ValueError('invalid discovery process bounds')
    chunks = []
    exceeded = threading.Event()
    process = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

    def drain(stream, retain):
        size = 0
        while block := stream.read(65536):
            size += len(block)
            if size > max_output:
                exceeded.set()
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
                return
            if retain:
                chunks.append(block)

    threads = [threading.Thread(target=drain, args=(process.stdout, True), daemon=True),
               threading.Thread(target=drain, args=(process.stderr, False), daemon=True)]
    try:
        for thread in threads:
            thread.start()
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            raise RuntimeError('public YouTube discovery timed out') from None
        for thread in threads:
            thread.join(timeout=2)
        if exceeded.is_set() or any(thread.is_alive() for thread in threads):
            raise RuntimeError('public YouTube discovery exceeded output bounds')
        if code:
            raise RuntimeError('public YouTube discovery failed; no capture was committed')
        return b''.join(chunks)
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
        for thread in threads:
            thread.join(timeout=2)
        process.stdout.close()
        process.stderr.close()


def optional_text(value):
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 1000:
        raise ValueError('invalid public metadata field')
    return value


def discover(source, *, limit=10, start=1, allow_fetch=False, runner=run):
    """Discover an explicit public window; selection alone never authorizes fetching."""
    if type(limit) is not int or not 1 <= limit <= 100 or type(start) is not int or not 1 <= start <= 10000:
        raise ValueError('limit must be 1..100 and start must be 1..10000')
    selected = selection(source)
    result = {'selection': selected, 'entries': [], 'unresolved': 0, 'start': start,
              'limit': limit, 'mutates_source': False, 'changes': False,
              'content_trust': 'untrusted', 'coverage': 'selected window; completeness unknown'}
    if selected['kind'] == 'video':
        if start != 1:
            raise ValueError('single-video input does not accept a playlist offset')
        result['entries'] = [{'key': selected['key'], 'url': selected['url'], 'title': None,
                              'author': None, 'date': None, 'availability': None}]
        return result
    if not allow_fetch:
        raise FetchApprovalRequired('public YouTube enumeration requires --allow-fetch')
    raw = runner(command(selected['url'], start, limit))
    if not isinstance(raw, bytes) or len(raw) > MAX_OUTPUT:
        raise ValueError('invalid discovery response size')
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise ValueError('invalid discovery JSON') from None
    if not isinstance(payload, dict) or not isinstance(payload.get('entries'), list) or len(payload['entries']) > limit:
        raise ValueError('discovery did not return the bounded playlist window')
    seen = set()
    for entry in payload['entries']:
        if entry is None:
            result['unresolved'] += 1
            continue
        if not isinstance(entry, dict) or not isinstance(entry.get('id'), str) or not VIDEO_ID.fullmatch(entry['id']):
            raise ValueError('discovery entry has no valid video identity')
        code = entry['id']
        if code in seen:
            continue
        seen.add(code)
        result['entries'].append({'key': f'youtube:{code}', 'url': f'https://www.youtube.com/watch?v={code}',
                                  'title': optional_text(entry.get('title')),
                                  'author': optional_text(entry.get('channel')),
                                  'date': optional_text(entry.get('upload_date')),
                                  'availability': optional_text(entry.get('availability'))})
    return result
