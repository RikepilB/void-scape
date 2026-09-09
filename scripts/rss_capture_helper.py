"""Bounded public feed capture; retained entries remain pending analysis."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skill/scripts'))
import article
from triage_store import checked, digest, encoded, exclusive, file_digest, locked

MAX_BYTES = 4 * 1024 * 1024


class FetchApprovalRequired(PermissionError):
    """The caller has not authorized this public feed request."""


def feed_url(value):
    """Use explicit public URLs; only Substack publication roots imply /feed."""
    safe, redacted = article._evidence_url(value)
    if redacted:
        # Do not silently change functional queries or persist subscription tokens.
        raise ValueError('feed URL must be canonical and contain no query or fragment')
    parsed = urlsplit(safe)
    if parsed.hostname.endswith('.substack.com') and parsed.path in {'', '/'}:
        safe = safe.rstrip('/') + '/feed'
    return safe


def timestamp(value):
    if not value:
        return None
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        try:
            result = parsedate_to_datetime(value)
        except (ValueError, TypeError, OverflowError):
            return None
    return result.astimezone(timezone.utc) if result.tzinfo is not None else None


def load_feed(source, *, identity_url=None, allow_fetch=False):
    if source.startswith(('https://', 'http://')):
        url = feed_url(source)
        if identity_url is not None:
            raise ValueError('remote source already defines its feed identity')
        if not allow_fetch:
            raise FetchApprovalRequired('public feed fetch requires --allow-fetch')
        text = article._fetch_url(url)
    else:
        if identity_url is None:
            raise ValueError('local feed requires --feed-url for stable identity')
        url = feed_url(identity_url)
        path = checked(source)
        with path.open('rb') as stream:
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError('feed exceeds 4 MiB')
        text = raw.decode('utf-8-sig')
    if len(text.encode('utf-8')) > MAX_BYTES:
        raise ValueError('feed exceeds 4 MiB')
    return url, article._parse_feed_xml(text)


def read_record(path):
    with checked(path).open('rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('capture record exceeds limit')
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError('capture record must be an object')
    return result


def verify(root, identity):
    if not re.fullmatch('[a-f0-9]{64}', identity):
        raise ValueError('invalid capture identity')
    folder = checked(checked(root) / '.rss-capture' / identity)
    entry = read_record(folder / 'entry.json')
    marker = read_record(folder / 'captured.json')
    if (not isinstance(entry.get('entry'), dict) or
            entry.get('schema') != 1 or entry.get('key') != f'rss:{identity}' or
            digest(encoded([entry.get('feed_url'), entry.get('entry', {}).get('guid')])) != identity or
            marker != {'schema': 1, 'key': entry['key'], 'sha256': digest(encoded(entry))} or
            file_digest(folder / 'entry.json') != marker['sha256']):
        raise ValueError('retained entry verification failed')
    return entry


def select(url, feed, *, since=None, limit=10):
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('limit must be between 1 and 100')
    cutoff = None
    if since is not None:
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', since):
            raise ValueError('since must be YYYY-MM-DD')
        cutoff = datetime.strptime(since, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    if len(feed['entries']) + len(feed['skipped']) > 10000:
        raise ValueError('feed has too many entries')
    result = []
    for entry in feed['entries']:
        observed = timestamp(entry['published'])
        if cutoff is not None and observed is not None and observed < cutoff:
            continue
        # Unknown dates stay visible instead of silently losing eligible entries.
        identity = digest(encoded([url, entry['guid']]))
        result.append({'schema': 1, 'key': f'rss:{identity}', 'feed_url': url,
                       'publication': feed['feed_title'], 'entry': entry,
                       'content_trust': 'untrusted'})
    return result


def capture(source, root, *, identity_url=None, allow_fetch=False, since=None, limit=10, apply=False):
    # Validate bounds before network access or local state creation.
    select('', {'entries': [], 'skipped': []}, since=since, limit=limit)
    root = checked(root)
    url, feed = load_feed(source, identity_url=identity_url, allow_fetch=allow_fetch)
    records = select(url, feed, since=since, limit=limit)
    if any(len(encoded(record)) > MAX_BYTES for record in records):
        raise ValueError('entry exceeds capture limit')

    def run():
        results = []
        duplicates = 0
        for record in records:
            identity = record['key'][4:]
            folder = checked(root / '.rss-capture' / identity)
            if (folder / 'captured.json').exists():
                retained = verify(root, identity)
                duplicates += 1
                if retained != record:
                    # Same ID, changed feed payload: preserve the original for review.
                    results.append({'key': record['key'], 'status': 'changed', 'analysis': 'unverified'})
                    if len(results) >= limit:
                        break
                continue
            result = {'key': record['key'], 'status': 'new', 'analysis': 'pending',
                      'title': record['entry']['title'],
                      'date_filter_uncertain': since is not None and timestamp(record['entry']['published']) is None}
            if apply:
                folder.mkdir(parents=True, exist_ok=True)
                exclusive(folder / 'entry.json', encoded(record))
                exclusive(folder / 'captured.json', encoded({'schema': 1, 'key': record['key'],
                                                           'sha256': digest(encoded(record))}))
                verify(root, identity)
                result.update(status='captured', evidence=str(folder / 'entry.json'))
            results.append(result)
            if len(results) >= limit:
                break
        return {'mode': 'capture' if apply else 'preview', 'results': results,
                'duplicates': duplicates, 'feed_skipped': feed['skipped'],
                'mutates_source': False, 'analyzed': 0, 'content_trust': 'untrusted'}

    if not apply:
        return run()
    with locked(root / '.rss-capture'):
        return run()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('--root', required=True)
    parser.add_argument('--feed-url', dest='identity_url')
    parser.add_argument('--allow-fetch', action='store_true')
    parser.add_argument('--since')
    parser.add_argument('--limit', type=int, default=10)
    parser.add_argument('--apply', action='store_true')
    try:
        data = capture(**vars(parser.parse_args(argv)))
        print(json.dumps({'ok': True, 'data': data, 'error': None,
                          'meta': {'command': 'rss_capture', 'content_trust': 'untrusted'}}, ensure_ascii=False))
        return 0
    except FetchApprovalRequired:
        print(json.dumps({'ok': False, 'data': None, 'error': {
            'code': 'rss_permission_required', 'exit_code': 4,
            'message': 'public feed fetch requires --allow-fetch', 'retryable': False},
            'meta': {'command': 'rss_capture', 'content_trust': 'untrusted'}}))
        return 4
    except (OSError, ValueError, KeyError, TypeError, RuntimeError):
        print(json.dumps({'ok': False, 'data': None, 'error': {
            'code': 'rss_capture_failed', 'message': 'feed capture failed; preserve artifacts and inspect locally',
            'exit_code': 6, 'retryable': False},
            'meta': {'command': 'rss_capture', 'content_trust': 'untrusted'}}))
        return 6


if __name__ == '__main__':
    raise SystemExit(main())
