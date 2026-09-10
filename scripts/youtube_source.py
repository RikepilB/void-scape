"""Closed public YouTube input scope for the ingest workflow."""
from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlsplit


VIDEO_ID = re.compile(r'[A-Za-z0-9_-]{11}')
TRACKING = {'si', 'feature', 'app', 'pp'}


def selection(value):
    """Normalize an unambiguous video, playlist or explicit channel tab URL."""
    if (not isinstance(value, str) or len(value) > 4096 or value != value.strip() or
            any(ord(c) < 33 for c in value)):
        raise ValueError('YouTube input must be a single URL without whitespace')
    parsed = urlsplit(value)
    if (parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port is not None or
            parsed.fragment or parsed.hostname not in {'youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtu.be'}):
        raise ValueError('expected an explicit public HTTPS YouTube URL')
    query = {}
    # Python 3.10 treats an empty query as a malformed field in strict mode.
    pairs = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True) if parsed.query else []
    for key, item in pairs:
        if key in query:
            raise ValueError('duplicate YouTube query parameter')
        query[key] = item
    functional = {key: item for key, item in query.items() if key not in TRACKING and not key.startswith('utm_')}
    path = parsed.path.rstrip('/')
    code = None
    if parsed.hostname == 'youtu.be':
        code = path.removeprefix('/')
    elif path == '/watch':
        code = functional.pop('v', None)
    elif re.fullmatch(r'/(shorts|embed|live)/[A-Za-z0-9_-]{11}', path):
        code = path.rsplit('/', 1)[1]
    if code is not None:
        if not VIDEO_ID.fullmatch(code) or functional:
            raise ValueError('video URL must identify one whole video without playlist or time scope')
        return {'kind': 'video', 'url': f'https://www.youtube.com/watch?v={code}', 'key': f'youtube:{code}'}
    if parsed.hostname == 'youtu.be':
        raise ValueError('invalid short YouTube URL')
    if path == '/playlist' and set(functional) == {'list'}:
        identity = functional['list']
        if not re.fullmatch(r'[A-Za-z0-9_-]{10,100}', identity):
            raise ValueError('expected a public playlist identifier')
        return {'kind': 'playlist', 'url': f'https://www.youtube.com/playlist?list={identity}', 'key': None}
    if functional:
        raise ValueError('unsupported YouTube query or ambiguous scope')
    channel = re.fullmatch(r'(/@[A-Za-z0-9_.-]{1,100}|/channel/UC[A-Za-z0-9_-]{22})(?:/(videos|shorts|streams))?', path)
    if channel:
        tab = channel[2] or 'videos'
        return {'kind': 'channel', 'url': f'https://www.youtube.com{channel[1]}/{tab}', 'key': None}
    raise ValueError('expected one video, public playlist or supported channel URL')
