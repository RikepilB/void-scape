"""Local note publication with immutable receipts and revalidated completion."""
from __future__ import annotations

import argparse
import errno
from contextlib import contextmanager
import hashlib
import html
import json
import os
from pathlib import Path
import re
import uuid

from instagram_capture_helper import canonical_url, extract_shortcode

INSTAGRAM_CATEGORIES = {
    'Codex-Code_Agent_Workflows', 'Job_Hunting_Interviews', 'AI_ML_Learning_Projects',
    'System_Design_CS_Fundamentals', 'Security_Privacy', 'Design_UI',
    'Startups_Business_Legal', 'Tools_Utilities', 'Off_Topic_Local', '_Skipped',
}
RSS_CATEGORIES = {'AI', 'Design', 'Product', 'Jobs', 'Content', 'Startup',
                  'Hackathon', 'Tech', 'Software_Developer', 'News', '_Skipped'}
YOUTUBE_CATEGORIES = set(RSS_CATEGORIES)
LINKEDIN_CATEGORIES = {'Writing', 'News', 'Resources', 'Concepts', 'Jobs', 'Events',
                       'Off_Topic', '_Skipped'}


def linkedin_provenance(key, metadata, capture_root):
    """Bind a note to a verified typed post observation, never an inferred ID."""
    from linkedin_capture_helper import location, verify as verify_capture
    if capture_root is None or not key.startswith('linkedin:'):
        raise ValueError('LinkedIn publication requires a verified capture root and key')
    identity = 'urn:li:' + key[len('linkedin:'):]
    entry = verify_capture(capture_root, identity)
    if any(metadata[field] != value for field, value in
           [('source', 'linkedin'), ('url', entry['url']), ('author', entry['author']), ('date', entry['date'])]):
        raise ValueError('LinkedIn frontmatter does not match retained provenance')
    folder, selected = location(capture_root, identity)
    return entry, [folder / 'entry.json', folder / 'captured.json']


def youtube_provenance(key, metadata, capture_root, read_root, *, skipped=False):
    """Require captured identity and completed reader evidence for video analysis."""
    from youtube_ingest_helper import capture_root as control_root, verify as verify_capture
    from youtube_read import verify_read
    if capture_root is None:
        raise ValueError('YouTube publication requires a verified capture root')
    entry = verify_capture(capture_root, key)
    if any(metadata[field] != value for field, value in
           [('source', 'youtube'), ('url', entry['url']), ('author', entry['author']), ('date', entry['date'])]):
        raise ValueError('YouTube frontmatter does not match retained provenance')
    folder = control_root(capture_root) / 'videos' / key[8:]
    evidence = [folder / 'entry.json', folder / 'captured.json']
    if skipped:
        if read_root is not None:
            raise ValueError('skip records do not claim completed reader evidence')
        return set(), evidence
    if read_root is None:
        raise ValueError('YouTube analysis requires completed reader evidence')
    ready, manifest, artifacts = verify_read(read_root, key)
    if ready['url'] != entry['url']:
        raise ValueError('read URL does not match the captured video')
    citations = {frame['t'] for frame in manifest.get('frames', [])}
    if manifest.get('transcript'):
        with checked(manifest['transcript']).open('rb') as stream:
            raw = stream.read(16 * 1024 * 1024 + 1)
        if len(raw) > 16 * 1024 * 1024:
            raise ValueError('transcript exceeds publication limit')
        citations.update(re.findall(r'^\[(\d{2,}:[0-5]\d(?::[0-5]\d)?)\]', raw.decode('utf-8'), re.MULTILINE))
    return citations, [*evidence, *artifacts]


def rss_provenance(key, metadata, capture_root):
    """Bind a draft to retained feed evidence, not a caller-invented URL."""
    from rss_capture_helper import verify as verify_capture
    import article
    if capture_root is None or not re.fullmatch('rss:[a-f0-9]{64}', key):
        raise ValueError('RSS publication requires a verified capture root and key')
    capture = verify_capture(capture_root, key[4:])
    entry = capture['entry']
    url = entry['link'] or capture['feed_url']
    try:
        url, _ = article._evidence_url(url)
    except ValueError:
        url = capture['feed_url']
    if (metadata['source'] != 'rss' or metadata['url'] != url or
            metadata['author'] != entry['author'] or metadata['date'] != (entry['published'] or None)):
        raise ValueError('RSS frontmatter does not match retained provenance')
    folder = checked(capture_root) / '.rss-capture' / key[4:]
    return entry, [folder / 'entry.json', folder / 'captured.json']


def note_metadata(text):
    """Accept a bounded scalar YAML subset; never resolve tags or references."""
    lines = text.splitlines()
    if not lines or lines[0] != '---' or '---' not in lines[1:20]:
        raise ValueError('note requires scalar frontmatter')
    end = lines.index('---', 1)
    result = {}
    for line in lines[1:end]:
        key, separator, value = line.partition(':')
        value = value.strip()
        if not separator or key in result:
            raise ValueError('invalid or duplicate frontmatter field')
        if value == 'null':
            parsed = None
        elif value.startswith('"'):
            parsed = json.loads(value)
            if not isinstance(parsed, str):
                raise ValueError('frontmatter must contain scalars')
        elif value.startswith("'"):
            if not re.fullmatch(r"'(?:[^']|'')*'", value):
                raise ValueError('invalid single-quoted frontmatter')
            parsed = value[1:-1].replace("''", "'")
        elif value and value[0] not in '!&*[{>|' and ': ' not in value:
            parsed = value
        else:
            raise ValueError('unsupported frontmatter value')
        result[key] = parsed
    if set(result) != {'source', 'url', 'author', 'date', 'category'}:
        raise ValueError('note frontmatter fields do not match contract')
    return result


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checked(path):
    path = Path(os.path.abspath(Path(path).expanduser()))
    for part in (*reversed(path.parents), path):
        if part.is_symlink() or (part.exists() and getattr(part.lstat(), 'st_file_attributes', 0) & 0x400):
            raise ValueError('triage paths cannot contain links or reparse points')
    return path


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def file_digest(path):
    path = checked(path)
    if not path.is_file():
        raise ValueError('artifact must be a regular file')
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def receipt_data(path):
    path = checked(path)
    with path.open('rb') as stream:
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError('receipt exceeds 1 MiB')
    record = json.loads(raw)
    identity = record['id']
    if not re.fullmatch('[a-f0-9]{64}', identity) or path.stem != identity:
        raise ValueError('receipt identity mismatch')
    if record['schema'] != 1 or record['status'] not in {'analyzed', 'skipped'}:
        raise ValueError('invalid receipt state')
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]{0,63}/' + identity + r'\.md', record['note']):
        raise ValueError('invalid receipt note path')
    return record


def exclusive(path, data):
    checked(path)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError('existing triage artifact differs; refusing overwrite')
        # Retry after a failed fsync must not trust merely visible bytes.
        with path.open('r+b') as stream:
            os.fsync(stream.fileno())
        return
    stage = path.with_name(f'.triage-write-{uuid.uuid4().hex}.tmp')
    with stage.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    # A hard link publishes atomically without replacing a preexisting name.
    # If interrupted, an unreferenced staging file is safe to leave for review.
    os.link(stage, path)
    stage.unlink()


class TriageBusyError(OSError):
    """Another process owns the publication lock."""


@contextmanager
def locked(root):
    """Use a process lock released by the OS even after a crashed publisher."""
    root = checked(root)
    root.mkdir(parents=True, exist_ok=True)
    control = checked(root / '.triage')
    control.mkdir(exist_ok=True)
    path = checked(control / 'lock')
    with path.open('a+b') as stream:
        if path.stat().st_size == 0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            if error.errno in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                raise TriageBusyError('publication lock is already held') from None
            raise
        try:
            yield root, control
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def prepare(source, key, category, note, evidence, *, skipped=False, capture_root=None, read_root=None):
    """Validate a caller-authored note without interpreting it as instructions."""
    if not re.fullmatch(r'[a-z][a-z0-9_-]{0,31}', source):
        raise ValueError('invalid source')
    if source not in {'instagram', 'rss', 'youtube', 'linkedin'}:
        raise ValueError('source adapter not implemented')
    if not key or len(key) > 2048 or any(c in key for c in '\r\n\x00'):
        raise ValueError('invalid canonical source key')
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]{0,63}', category):
        raise ValueError('invalid category')
    if category not in {'instagram': INSTAGRAM_CATEGORIES, 'rss': RSS_CATEGORIES,
                       'youtube': YOUTUBE_CATEGORIES, 'linkedin': LINKEDIN_CATEGORIES}[source]:
        raise ValueError('category is not registered for the source')
    if skipped != (category == '_Skipped'):
        raise ValueError('skip records belong in _Skipped')
    if source != 'youtube' and read_root is not None:
        raise ValueError('reader binding is only implemented for YouTube')
    with checked(note).open('rb') as stream:
        raw = stream.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError('note exceeds 4 MiB')
    text = raw.decode('utf-8')
    metadata = note_metadata(text)
    if not isinstance(metadata['url'], str):
        raise ValueError('source URL is required')
    if metadata['category'] != category:
        raise ValueError('note provenance does not match the requested source')
    if source == 'instagram':
        code = extract_shortcode(metadata['url'])
        if (capture_root is not None or metadata['source'] != source or
                metadata['url'] != canonical_url(code) or key != f'instagram:{code}'):
            raise ValueError('note provenance does not match the requested source')
    elif source == 'rss':
        entry, retained = rss_provenance(key, metadata, capture_root)
        evidence = list(dict.fromkeys([*retained, *map(Path, evidence)]))
    elif source == 'linkedin':
        entry, retained = linkedin_provenance(key, metadata, capture_root)
        evidence = list(dict.fromkeys([*retained, *map(Path, evidence)]))
    else:
        citations, retained = youtube_provenance(key, metadata, capture_root, read_root, skipped=skipped)
        evidence = list(dict.fromkeys([*retained, *map(Path, evidence)]))
    if [line for line in text.splitlines() if line.startswith('Source:')] != [f'Source: {key}']:
        raise ValueError('note must contain exactly one matching Source line')
    required = ('## Reason',) if skipped else ('## Synopsis', '## Action Items',
                {'instagram': '## Instagram Excerpt', 'rss': '## RSS Excerpt',
                 'youtube': '## Key moments', 'linkedin': '## Post Excerpt'}[source],
                '## Links', '## Evidence')
    if source == 'rss' and not skipped:
        required += ('## Key points',)
    if any(text.splitlines().count(section) != 1 for section in required):
        raise ValueError('note is missing required sections')
    if source == 'youtube' and not skipped:
        cited = set(re.findall(r'\[(\d{2,}:[0-5]\d(?::[0-5]\d)?)\]', text))
        moments = re.search(r'^## Key moments\r?\n(.*?)(?=^## |\Z)', text, re.MULTILINE | re.DOTALL)[1]
        if not cited or not cited <= citations or not re.search(r'\[\d{2,}:[0-5]\d(?::[0-5]\d)?\]', moments):
            raise ValueError('YouTube notes require actual reader timestamps in key moments')
    if source in {'rss', 'linkedin'} and not skipped:
        heading = 'RSS Excerpt' if source == 'rss' else 'Post Excerpt'
        label = 'RSS' if source == 'rss' else 'LinkedIn'
        section = re.search(r'^## ' + heading + r'\r?\n(.*?)(?=^## |\Z)', text, re.MULTILINE | re.DOTALL)[1]
        lines = [line.strip() for line in section.splitlines() if line.strip()]
        if len(lines) != 2 or lines[0] != 'Untrusted source content:' or not lines[1].startswith('> '):
            raise ValueError(f'{label} excerpt must be a labeled single-line quotation')
        quote = lines[1][2:]
        if not quote or len(quote.split()) > 25 or quote not in entry['body' if source == 'rss' else 'text']:
            raise ValueError(f'{label} excerpt must be short and verbatim from retained content')
    titles = re.findall(r'^# ([^\r\n]+)\r?$', text, re.MULTILINE)
    if len(titles) != 1 or len(titles[0]) > 200:
        raise ValueError('note requires one bounded title')
    priorities = re.findall(r'^Priority: \*\*(High|Medium|Low)\*\* [—-] .+$', text, re.MULTILINE)
    if not skipped and len(priorities) != 1:
        raise ValueError('analysis note requires a priority and reason')
    if not skipped and not evidence:
        raise ValueError('completed analysis requires retained evidence')
    if len(evidence) > (515 if source == 'youtube' else 100):
        raise ValueError('too many evidence files')
    artifacts = []
    for item in evidence:
        path = checked(item)
        if not path.is_file():
            raise ValueError('evidence must be a regular file')
        artifacts.append({'path': str(path), 'sha256': file_digest(path)})
    if not skipped:
        links = '\n'.join(f"- [Evidence {number}](<{Path(item['path']).as_uri()}>)"
                          for number, item in enumerate(artifacts, 1))
        text = re.sub(r'^## Evidence\r?$.*?(?=^## |\Z)',
                      lambda match: '## Evidence\n' + links + '\n\n',
                      text, flags=re.MULTILINE | re.DOTALL)
        raw = text.encode('utf-8')
    identity = digest(encoded({'source': source, 'key': key, 'category': category,
                               'note_sha256': digest(raw), 'evidence': artifacts,
                               'skipped': skipped}))
    record = {'schema': 1, 'id': identity, 'source': source, 'key': key,
              'title': titles[0], 'priority': None if skipped else priorities[0],
              'note': f'{category}/{identity}.md', 'note_sha256': digest(raw),
              'evidence': artifacts, 'status': 'skipped' if skipped else 'analyzed',
              'content_trust': 'untrusted'}
    if len(encoded(record)) > 1024 * 1024:
        raise ValueError('receipt exceeds 1 MiB')
    return record, raw


def lookup(root, source, key):
    """Find verified analysis separately from prior skipped attempts."""
    root = checked(root)
    control = checked(root / '.triage')
    results = {'analyzed': [], 'skipped': [], 'pending': []}
    if not control.exists():
        return results
    for receipt in control.glob('*.json'):
        record = receipt_data(receipt)
        if record['source'] == source and record['key'] == key:
            result = inspect(root, record['id'])
            results[result['status']].append({'id': record['id'], **result})
    return results


def verify(root, record):
    """Check durable contents every time; a receipt is not evidence by itself."""
    path = checked(root / record['note'])
    path.relative_to(root)
    if file_digest(path) != record['note_sha256']:
        raise ValueError('published note changed')
    for item in record['evidence']:
        if file_digest(item['path']) != item['sha256']:
            raise ValueError('retained evidence changed')


def index_line(record):
    title = html.escape(record['title']).replace('\\', '\\\\').replace('[', '\\[').replace(']', '\\]')
    return f"- [{title}]({record['note']}) — {record['status']} / {record['priority'] or 'N/A'}\n"


def update_index(root, control, record):
    """Only this serialized publisher writes the derivative index."""
    header = '# Triage index\n\n<!-- managed by triage_store v1 -->\n'
    path = checked(root / '_index.md')
    allowed = {}
    for receipt in control.glob('*.json'):
        value = receipt_data(receipt)
        if value['id'] != record['id']:
            marker = checked(control / f"{value['id']}.done")
            if not marker.is_file():
                continue
            if marker.read_bytes() != digest(encoded(value)).encode():
                raise ValueError('receipt changed')
        verify(root, value)
        allowed[index_line(value)] = value
    current = path.read_text(encoding='utf-8') if path.exists() else header
    if not current.startswith(header) or any(line not in allowed for line in current[len(header):].splitlines(keepends=True)):
        raise ValueError('index has unrecognized edits; refusing overwrite')
    line = index_line(record)
    if line in current[len(header):].splitlines(keepends=True):
        return
    stage = checked(control / f'index-{uuid.uuid4().hex}.tmp')
    exclusive(stage, (current + line).encode())
    stage.replace(path)


def publish(root, source, key, category, note, evidence, *, skipped=False, capture_root=None, read_root=None):
    record, raw = prepare(source, key, category, note, evidence, skipped=skipped, capture_root=capture_root, read_root=read_root)
    with locked(root) as (root, control):
        if source in {'rss', 'youtube', 'linkedin'}:
            previous = lookup(root, source, key)
            completed = previous['analyzed'] or (previous['skipped'] if skipped else [])
            if completed:
                return {**completed[0], 'duplicate': True}
        receipt = control / f"{record['id']}.json"
        exclusive(receipt, encoded(record))
        target = checked(root / record['note'])
        target.parent.mkdir(exist_ok=True)
        exclusive(target, raw)
        verify(root, record)
        update_index(root, control, record)
        exclusive(control / f"{record['id']}.done", digest(encoded(record)).encode())
        return {'status': record['status'], 'note': str(target), 'id': record['id'],
                'artifact_verified': True, 'source_action_authorized': False}


def inspect(root, identity):
    if not re.fullmatch('[a-f0-9]{64}', identity):
        raise ValueError('invalid receipt ID')
    root = checked(root)
    control = checked(root / '.triage')
    record = receipt_data(control / f'{identity}.json')
    marker = checked(control / f'{identity}.done')
    complete = marker.is_file() and marker.read_bytes() == digest(encoded(record)).encode()
    if not complete:
        return {'status': 'pending', 'artifact_verified': False, 'source_action_authorized': False}
    verify(root, record)
    index = checked(root / '_index.md')
    complete = complete and index.is_file() and index_line(record) in index.read_text(encoding='utf-8').splitlines(keepends=True)
    return {'status': record['status'] if complete else 'pending', 'artifact_verified': complete,
            'source_action_authorized': False, 'note': str(root / record['note'])}


def main(argv=None):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    read = sub.add_parser('inspect')
    read.add_argument('root')
    read.add_argument('id')
    find = sub.add_parser('lookup')
    for field in ('root', 'source', 'key'):
        find.add_argument(field)
    write = sub.add_parser('publish')
    for field in ('root', 'source', 'key', 'category', 'note'):
        write.add_argument(field)
    write.add_argument('--evidence', action='append', default=[])
    write.add_argument('--skipped', action='store_true')
    write.add_argument('--capture-root')
    write.add_argument('--read-root')
    args = vars(parser.parse_args(argv))
    command = args.pop('command')
    try:
        result = (inspect(args['root'], args['id']) if command == 'inspect' else
                  lookup(**args) if command == 'lookup' else publish(**args))
        print(json.dumps({'ok': True, 'data': result, 'error': None,
                          'meta': {'command': command, 'content_trust': 'untrusted'}}))
        return 0
    except (OSError, ValueError, KeyError, TypeError):
        print(json.dumps({'ok': False, 'data': None,
                          'error': {'code': 'triage_verification_failed', 'exit_code': 6,
                                    'retryable': False,
                                    'message': 'triage verification failed; preserve artifacts and review locally'},
                          'meta': {'command': command, 'content_trust': 'untrusted'}}))
        return 6


if __name__ == '__main__':
    raise SystemExit(main())
