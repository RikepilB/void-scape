"""Public YouTube capture snapshots and verified, selected-scope resume."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from triage_store import checked, digest, encoded, exclusive, file_digest, locked, lookup
from youtube_public import FetchApprovalRequired, discover, optional_text
from youtube_source import VIDEO_ID, selection


MAX_RECORD = 1024 * 1024


def read_json(path):
    with checked(path).open('rb') as stream:
        raw = stream.read(MAX_RECORD + 1)
    if len(raw) > MAX_RECORD:
        raise ValueError('YouTube capture record exceeds limit')
    return json.loads(raw)


def validate_entry(entry):
    if not isinstance(entry, dict) or set(entry) != {'key', 'url', 'title', 'author', 'date', 'availability'}:
        raise ValueError('invalid YouTube entry schema')
    selected = selection(entry['url'])
    if selected['kind'] != 'video' or selected['url'] != entry['url'] or selected['key'] != entry['key']:
        raise ValueError('YouTube entry identity mismatch')
    for field in ('title', 'author', 'date', 'availability'):
        optional_text(entry[field])
    return entry


def validate_snapshot(record):
    if not isinstance(record, dict) or set(record) != {'schema', 'selection', 'entries', 'start', 'limit', 'unresolved', 'content_trust'}:
        raise ValueError('invalid YouTube selection schema')
    if record['schema'] != 1 or record['content_trust'] != 'untrusted':
        raise ValueError('invalid YouTube selection version')
    if not isinstance(record['selection'], dict) or selection(record['selection']['url']) != record['selection']:
        raise ValueError('invalid YouTube selection identity')
    if (type(record['start']) is not int or not 1 <= record['start'] <= 10000 or
            type(record['limit']) is not int or not 1 <= record['limit'] <= 100 or
            type(record['unresolved']) is not int or not 0 <= record['unresolved'] <= record['limit'] or
            not isinstance(record['entries'], list) or len(record['entries']) + record['unresolved'] > record['limit']):
        raise ValueError('invalid YouTube selection bounds')
    keys = [validate_entry(entry)['key'] for entry in record['entries']]
    if len(keys) != len(set(keys)):
        raise ValueError('duplicate identity in YouTube selection')
    if record['selection']['kind'] == 'video' and (record['start'] != 1 or keys != [record['selection']['key']] or record['unresolved']):
        raise ValueError('single-video selection changed scope')
    return record


def capture_root(root):
    return checked(checked(root) / '.youtube-capture')


def read_snapshot(root, identity):
    if not isinstance(identity, str) or not re.fullmatch('[a-f0-9]{64}', identity):
        raise ValueError('invalid YouTube selection ID')
    path = checked(capture_root(root) / 'selections' / f'{identity}.json')
    record = validate_snapshot(read_json(path))
    if digest(encoded(record)) != identity or file_digest(path) != identity:
        raise ValueError('YouTube selection changed')
    return record


def verify(root, key):
    if not isinstance(key, str) or not key.startswith('youtube:') or not VIDEO_ID.fullmatch(key[8:]):
        raise ValueError('invalid YouTube capture key')
    folder = checked(capture_root(root) / 'videos' / key[8:])
    record = read_json(folder / 'entry.json')
    if not isinstance(record, dict) or set(record) != {'schema', 'entry', 'content_trust'} or record['schema'] != 1 or record['content_trust'] != 'untrusted':
        raise ValueError('invalid retained YouTube record')
    entry = validate_entry(record['entry'])
    marker = read_json(folder / 'captured.json')
    if (entry['key'] != key or marker != {'schema': 1, 'key': key, 'sha256': digest(encoded(record))} or
            file_digest(folder / 'entry.json') != marker['sha256']):
        raise ValueError('retained YouTube evidence changed')
    return entry


def process_snapshot(root, record, *, apply=False):
    record = validate_snapshot(record)
    root = checked(root)
    control = capture_root(root)
    identity = digest(encoded(record))

    def process():
        results = []
        if apply:
            folder = checked(control / 'selections')
            folder.mkdir(parents=True, exist_ok=True)
            exclusive(folder / f'{identity}.json', encoded(record))
            read_snapshot(root, identity)
        for entry in record['entries']:
            folder = checked(control / 'videos' / entry['key'][8:])
            item = {'key': entry['key'], 'status': 'new', 'analysis': 'unverified'}
            if (folder / 'captured.json').exists():
                retained = verify(root, entry['key'])
                item.update(status='duplicate', metadata_changed=retained != entry)
            elif apply:
                folder.mkdir(parents=True, exist_ok=True)
                retained = {'schema': 1, 'entry': entry, 'content_trust': 'untrusted'}
                exclusive(folder / 'entry.json', encoded(retained))
                exclusive(folder / 'captured.json', encoded({'schema': 1, 'key': entry['key'], 'sha256': digest(encoded(retained))}))
                verify(root, entry['key'])
                item['status'] = 'captured'
            results.append(item)
        if apply:
            exclusive(control / 'selections' / f'{identity}.done', identity.encode())
        return {'snapshot': identity, 'results': results, 'unresolved': record['unresolved'],
                'mode': 'capture' if apply else 'preview', 'changes': apply,
                'mutates_source': False, 'analyzed': 0, 'content_trust': 'untrusted'}

    if apply:
        with locked(control):
            return process()
    return process()


def capture(source, root, *, limit=10, start=1, allow_fetch=False, apply=False, discoverer=discover):
    checked(root)
    discovery = discoverer(source, limit=limit, start=start, allow_fetch=allow_fetch)
    record = {'schema': 1, 'selection': discovery['selection'], 'entries': discovery['entries'],
              'start': discovery['start'], 'limit': discovery['limit'], 'unresolved': discovery['unresolved'],
              'content_trust': 'untrusted'}
    return process_snapshot(root, record, apply=apply)


def retained(root, identity, notes_root):
    """Read exactly a retained selection, even after the remote playlist changes."""
    notes_root = checked(notes_root)
    record = read_snapshot(root, identity)
    result = {'snapshot': identity, 'results': [], 'analyzed': 0, 'skipped': 0,
              'incomplete': 0, 'unresolved': record['unresolved'], 'changes': False,
              'mutates_source': False, 'content_trust': 'untrusted'}
    for entry in record['entries']:
        folder = checked(capture_root(root) / 'videos' / entry['key'][8:])
        if not (folder / 'captured.json').exists():
            result['incomplete'] += 1
            continue
        verify(root, entry['key'])
        state = lookup(notes_root, 'youtube', entry['key'])
        if state['analyzed']:
            result['analyzed'] += 1
        elif state['skipped']:
            result['skipped'] += 1
        else:
            result['results'].append({'key': entry['key'], 'url': entry['url'], 'status': 'needs_note',
                                      'publication_pending': bool(state['pending']), 'evidence': str(folder / 'entry.json')})
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    new = sub.add_parser('capture')
    new.add_argument('source')
    new.add_argument('--root', required=True)
    new.add_argument('--limit', type=int, default=10)
    new.add_argument('--start', type=int, default=1)
    new.add_argument('--allow-fetch', action='store_true')
    new.add_argument('--apply', action='store_true')
    resume = sub.add_parser('resume')
    listing = sub.add_parser('retained')
    for command in (resume, listing):
        command.add_argument('--root', required=True)
        command.add_argument('--snapshot', dest='identity', required=True)
    resume.add_argument('--apply', action='store_true')
    listing.add_argument('--notes-root', required=True)
    options = vars(parser.parse_args(argv))
    command = options.pop('command')
    try:
        if command == 'capture':
            result = capture(**options)
        elif command == 'resume':
            result = process_snapshot(options['root'], read_snapshot(options['root'], options['identity']), apply=options['apply'])
        else:
            result = retained(**options)
        print(json.dumps({'ok': True, 'data': result, 'error': None, 'meta': {'command': command, 'content_trust': 'untrusted'}}))
        return 0
    except FetchApprovalRequired:
        print(json.dumps({'ok': False, 'data': None, 'error': {'code': 'fetch_approval_required', 'exit_code': 4,
                          'message': 'Public YouTube enumeration requires explicit fetch authorization', 'retryable': False},
                          'meta': {'command': command, 'content_trust': 'untrusted'}}))
        return 4
    except (OSError, ValueError, KeyError, TypeError, RuntimeError):
        print(json.dumps({'ok': False, 'data': None, 'error': {'code': 'youtube_ingest_failed', 'exit_code': 6,
                          'message': 'YouTube intake failed; preserve retained artifacts and inspect locally', 'retryable': False},
                          'meta': {'command': command, 'content_trust': 'untrusted'}}))
        return 6


if __name__ == '__main__':
    raise SystemExit(main())
