"""Validate and retain selected LinkedIn observations; no browser or network."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import re
from urllib.parse import parse_qsl, unquote, urlsplit

from triage_store import checked, digest, encoded, exclusive, file_digest, locked


IDENTITY = re.compile(r'urn:li:(activity|share|ugcPost):([1-9][0-9]{9,21})')
MAX_RECORD = 256 * 1024


def selection(value):
    if (not isinstance(value, str) or len(value) > 4096 or
            any(ord(c) <= 32 or ord(c) == 127 for c in value)):
        raise ValueError('expected one explicit LinkedIn identity')
    match = IDENTITY.fullmatch(value)
    if not match:
        parsed = urlsplit(value)
        if (parsed.scheme != 'https' or parsed.hostname not in {'linkedin.com', 'www.linkedin.com'} or
                parsed.username is not None or parsed.password is not None or
                parsed.port is not None or parsed.fragment):
            raise ValueError('expected an explicit LinkedIn post URL')
        query = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True) if parsed.query else []
        seen = set()
        for key, _ in query:
            if key in seen or not (key.startswith('utm_') or key == 'rcm'):
                raise ValueError('unsupported or duplicate LinkedIn query parameter')
            seen.add(key)
        path = unquote(parsed.path).rstrip('/')
        match = IDENTITY.fullmatch(path.removeprefix('/feed/update/')) if path.startswith('/feed/update/') else None
        if not match:
            post = re.fullmatch(r'/posts/[A-Za-z0-9_-]+[_-]activity-([1-9][0-9]{9,21})-[A-Za-z0-9_-]{1,64}', path)
            if post:
                match = IDENTITY.fullmatch(f'urn:li:activity:{post[1]}')
        if not match:
            raise ValueError('unsupported LinkedIn post identity; do not infer from event or job IDs')
    urn = match[0]
    return {'key': f'linkedin:{match[1]}:{match[2]}', 'urn': urn,
            'url': f'https://www.linkedin.com/feed/update/{urn}/'}


def validate(observation):
    if not isinstance(observation, dict) or set(observation) != {'url', 'text', 'author', 'date', 'observed_at', 'kind'}:
        raise ValueError('invalid observation schema')
    selected = selection(observation['url'])
    body = observation['text']
    if not isinstance(body, str) or not body.strip() or len(body.encode('utf-8')) > 128 * 1024 or '\x00' in body:
        raise ValueError('expected bounded visible post text')
    for field in ('author', 'date'):
        value = observation[field]
        if value is not None and (not isinstance(value, str) or len(value) > 1000 or '\x00' in value):
            raise ValueError('invalid observed metadata')
    stamp = observation['observed_at']
    if not isinstance(stamp, str) or len(stamp) > 40:
        raise ValueError('capture time required')
    observed = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
    if observed.tzinfo is None:
        raise ValueError('capture time must include a timezone')
    if observation['kind'] not in {'post', 'article', 'job', 'event'}:
        raise ValueError('unsupported observed content kind')
    return {**observation, **selected, 'observed_at': observed.isoformat()}


def read_json(path):
    with checked(path).open('rb') as stream:
        raw = stream.read(MAX_RECORD + 1)
    if len(raw) > MAX_RECORD:
        raise ValueError('observation exceeds limit')
    return json.loads(raw)


def location(root, identity):
    selected = selection(identity)
    return checked(checked(root) / '.linkedin-capture' / digest(selected['key'].encode())), selected


def verify(root, identity):
    folder, selected = location(root, identity)
    record = read_json(folder / 'entry.json')
    if not isinstance(record, dict) or set(record) != {'schema', 'entry', 'content_trust'} or record['schema'] != 1 or record['content_trust'] != 'untrusted':
        raise ValueError('invalid retained LinkedIn record')
    entry = record['entry']
    if not isinstance(entry, dict) or set(entry) != {'url', 'text', 'author', 'date', 'observed_at', 'kind', 'key', 'urn'}:
        raise ValueError('invalid retained LinkedIn entry')
    base = {key: value for key, value in entry.items() if key not in {'key', 'urn'}}
    if validate(base) != entry or entry['key'] != selected['key']:
        raise ValueError('retained identity mismatch')
    marker = read_json(folder / 'captured.json')
    if (marker != {'schema': 1, 'key': selected['key'], 'sha256': digest(encoded(record))} or
            file_digest(folder / 'entry.json') != marker['sha256']):
        raise ValueError('retained LinkedIn evidence changed')
    return entry


def capture(root, observation, *, apply=False):
    entry = validate(observation)
    folder, selected = location(root, entry['urn'])
    record = {'schema': 1, 'entry': entry, 'content_trust': 'untrusted'}
    raw = encoded(record)
    if len(raw) > MAX_RECORD:
        raise ValueError('encoded observation exceeds limit')

    def process():
        result = {**selected, 'status': 'new', 'changes': False, 'analyzed': False,
                  'source_action_authorized': False, 'content_trust': 'untrusted'}
        if (folder / 'captured.json').exists():
            previous = verify(root, entry['urn'])
            return {**result, 'status': 'duplicate', 'observation_changed': previous != entry}
        if apply:
            folder.mkdir(parents=True, exist_ok=True)
            exclusive(folder / 'entry.json', raw)
            if read_json(folder / 'entry.json') != record or file_digest(folder / 'entry.json') != digest(raw):
                raise ValueError('capture verification failed')
            exclusive(folder / 'captured.json', encoded({'schema': 1, 'key': entry['key'], 'sha256': digest(raw)}))
            verify(root, entry['urn'])
            result.update(status='captured', changes=True)
        elif (folder / 'entry.json').exists():
            result['status'] = 'incomplete'
        return result

    if apply:
        with locked(checked(root) / '.linkedin-capture'):
            return process()
    return process()


def retained(root, identities):
    if not isinstance(identities, list) or not 1 <= len(identities) <= 100:
        raise ValueError('select between one and 100 identities')
    selections = [location(root, identity) for identity in identities]
    if len({selected['key'] for _, selected in selections}) != len(selections):
        raise ValueError('duplicate selected identity')
    results = []
    for folder, selected in selections:
        status = 'missing'
        if (folder / 'captured.json').exists():
            verify(root, selected['urn'])
            status = 'captured'
        elif (folder / 'entry.json').exists():
            status = 'incomplete'
        results.append({**selected, 'status': status, 'analyzed': False})
    return {'results': results, 'changes': False, 'source_action_authorized': False,
            'content_trust': 'untrusted'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    inspect = sub.add_parser('inspect')
    inspect.add_argument('identity')
    new = sub.add_parser('capture')
    new.add_argument('observation', help='bounded local JSON observation file')
    new.add_argument('--root', required=True)
    new.add_argument('--apply', action='store_true')
    resume = sub.add_parser('retained')
    resume.add_argument('identities', nargs='+')
    resume.add_argument('--root', required=True)
    args = vars(parser.parse_args(argv))
    command = args.pop('command')
    try:
        if command == 'inspect':
            data = selection(args['identity'])
        elif command == 'capture':
            data = capture(args['root'], read_json(args['observation']), apply=args['apply'])
        else:
            data = retained(**args)
        print(json.dumps({'ok': True, 'data': data, 'error': None}))
        return 0
    except (OSError, ValueError, TypeError, KeyError, RuntimeError):
        print(json.dumps({'ok': False, 'data': None, 'error': {'code': 'linkedin_capture_failed',
                          'message': 'LinkedIn capture validation or storage failed; preserve retained evidence'}}))
        return 6


if __name__ == '__main__':
    raise SystemExit(main())
