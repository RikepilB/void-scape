import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

import triage_store as store


def header(category='Tools_Utilities'):
    return f'---\nsource: instagram\nurl: https://www.instagram.com/reel/Example123/\nauthor: null\ndate: null\ncategory: {category}\n---\n'


def fixture(tmp_path):
    note = tmp_path / 'draft.md'
    note.write_text(header() + '# Synthetic\nSource: instagram:Example123\nPriority: **Medium** — Example.\n## Synopsis\nExample.\n## Action Items\nNone.\n## Instagram Excerpt\nExample.\n## Links\n## Evidence\n', encoding='utf-8')
    evidence = tmp_path / 'transcript.txt'
    evidence.write_text('[00:00] Synthetic evidence')
    return dict(root=tmp_path / 'notes', source='instagram', key='instagram:Example123',
                category='Tools_Utilities', note=note, evidence=[evidence])


def test_publish_verify_and_duplicate(tmp_path):
    args = fixture(tmp_path)
    result = store.publish(**args)
    assert result['artifact_verified'] and not result['source_action_authorized']
    before = (args['root'] / '_index.md').read_bytes()
    assert store.publish(**args) == result
    assert (args['root'] / '_index.md').read_bytes() == before
    assert store.inspect(args['root'], result['id'])['status'] == 'analyzed'


@pytest.mark.parametrize('field,value', [
    ('source', '../instagram'), ('source', 'unsupported'),
    ('key', ''), ('key', 'instagram:Example123\nextra'),
    ('category', '../Tools'), ('category', 'Unregistered'),
    ('category', '_Skipped'),
])
def test_invalid_request_never_creates_store(tmp_path, field, value):
    args = fixture(tmp_path)
    args[field] = value
    with pytest.raises(ValueError):
        store.publish(**args)
    assert not args['root'].exists()


@pytest.mark.parametrize('old,new', [
    ('author: null', 'author: null\nauthor: repeated'),
    ('author: null', 'author: !custom tagged'),
    ('author: null', 'unknown: null'),
    ('url: https://www.instagram.com/reel/Example123/', 'url: null'),
    ('Source: instagram:Example123', 'Source: instagram:Other123'),
    ('## Synopsis', '## Wrong'),
    ('# Synthetic\n', '# One\n# Two\n'),
    ('Priority: **Medium** — Example.', 'Priority: unknown'),
])
def test_invalid_draft_is_preserved_without_publication(tmp_path, old, new):
    args = fixture(tmp_path)
    text = args['note'].read_text(encoding='utf-8').replace(old, new)
    args['note'].write_text(text, encoding='utf-8')
    with pytest.raises(ValueError):
        store.publish(**args)
    assert args['note'].read_text(encoding='utf-8') == text
    assert not args['root'].exists()


def test_unrelated_receipt_is_not_a_duplicate(tmp_path):
    args = fixture(tmp_path)
    store.publish(**args)
    assert store.lookup(args['root'], 'instagram', 'instagram:Other123') == {
        'analyzed': [], 'skipped': [], 'pending': []}


def test_missing_evidence_stops_before_publication(tmp_path):
    args = fixture(tmp_path)
    args['evidence'] = [tmp_path / 'absent.txt']
    with pytest.raises(ValueError, match='regular file'):
        store.publish(**args)
    assert not args['root'].exists()


@pytest.mark.parametrize('target', ['note', 'evidence'])
def test_changed_artifact_revokes_verified_state(tmp_path, target):
    args = fixture(tmp_path)
    result = store.publish(**args)
    path = Path(result['note']) if target == 'note' else args['evidence'][0]
    path.write_text('changed')
    with pytest.raises(ValueError):
        store.inspect(args['root'], result['id'])
    with pytest.raises(ValueError):
        store.publish(**args)


def test_interruption_after_receipt_can_resume(tmp_path, monkeypatch):
    args = fixture(tmp_path)
    original = store.exclusive
    def interrupted(path, data):
        if path.suffix == '.md':
            raise OSError('synthetic interruption')
        original(path, data)
    monkeypatch.setattr(store, 'exclusive', interrupted)
    with pytest.raises(OSError):
        store.publish(**args)
    receipt = next((args['root'] / '.triage').glob('*.json'))
    identity = json.loads(receipt.read_text())['id']
    assert store.inspect(args['root'], identity)['status'] == 'pending'
    monkeypatch.setattr(store, 'exclusive', original)
    assert store.publish(**args)['artifact_verified']


def test_interruption_after_index_can_resume(tmp_path, monkeypatch):
    args = fixture(tmp_path)
    original = store.exclusive
    def interrupted(path, data):
        if path.suffix == '.done':
            raise OSError('synthetic interruption')
        original(path, data)
    monkeypatch.setattr(store, 'exclusive', interrupted)
    with pytest.raises(OSError):
        store.publish(**args)
    monkeypatch.setattr(store, 'exclusive', original)
    result = store.publish(**args)
    assert (args['root'] / '_index.md').read_text().count(result['id']) == 1


def test_modified_index_is_not_overwritten(tmp_path):
    args = fixture(tmp_path)
    store.publish(**args)
    index = args['root'] / '_index.md'
    index.write_text('User edits')
    with pytest.raises(ValueError, match='index'):
        store.publish(**args)
    assert index.read_text() == 'User edits'


def test_skip_is_recorded_without_authorizing_source_action(tmp_path):
    args = fixture(tmp_path)
    args.update(category='_Skipped', skipped=True, evidence=[])
    args['note'].write_text(header('_Skipped') + '# Skipped\nSource: instagram:Example123\n## Reason\nMissing dependency\n')
    result = store.publish(**args)
    assert result['status'] == 'skipped'
    assert result['source_action_authorized'] is False


def test_path_traversal_and_missing_evidence_fail_before_output(tmp_path):
    args = fixture(tmp_path)
    args['category'] = '../outside'
    with pytest.raises(ValueError):
        store.publish(**args)
    assert not args['root'].exists()
    args['category'] = 'Tools_Utilities'
    args['evidence'] = []
    with pytest.raises(ValueError):
        store.publish(**args)
    assert not args['root'].exists()


def test_concurrent_publisher_fails_closed(tmp_path):
    args = fixture(tmp_path)
    with store.locked(args['root']):
        with pytest.raises(OSError):
            store.publish(**args)


def test_inspect_does_not_create_missing_root(tmp_path):
    root = tmp_path / 'absent'
    with pytest.raises(OSError):
        store.inspect(root, 'a' * 64)
    assert not root.exists()


def test_skip_does_not_prevent_later_analysis(tmp_path):
    args = fixture(tmp_path)
    original = args['note'].read_text()
    args['note'].write_text(header('_Skipped') + '# Skipped\nSource: instagram:Example123\n## Reason\nMissing dependency\n')
    skipped = store.publish(**{**args, 'category': '_Skipped', 'skipped': True, 'evidence': []})
    args['note'].write_text(original)
    analyzed = store.publish(**args)
    assert analyzed['id'] != skipped['id']
    result = store.lookup(args['root'], args['source'], args['key'])
    assert len(result['analyzed']) == len(result['skipped']) == 1
    assert result['pending'] == []


@pytest.mark.parametrize('change', ['source', 'url', 'category', 'duplicate', 'section', 'frontmatter', 'quote', 'mapping', 'embedded_quote'])
def test_invalid_provenance_has_no_output(tmp_path, change):
    args = fixture(tmp_path)
    text = args['note'].read_text()
    replacements = {'source': ('source: instagram', 'source: other'),
                    'url': ('url: https://www.instagram.com/reel/Example123/', 'url: null'),
                    'category': ('category: Tools_Utilities', 'category: Security_Privacy'),
                    'duplicate': ('Source: instagram:Example123', 'Source: instagram:Example123\nSource: another'),
                    'section': ('## Synopsis', '## Missing'),
                    'frontmatter': ('author: null', 'author: !include secret'),
                    'quote': ('author: null', "author: 'unterminated"),
                    'mapping': ('author: null', 'author: nested: value'),
                    'embedded_quote': ('author: null', "author: 'O'Neil'")}
    args['note'].write_text(text.replace(*replacements[change]))
    with pytest.raises(ValueError):
        store.publish(**args)
    assert not args['root'].exists()


def test_cli_roundtrip(tmp_path):
    args = fixture(tmp_path)
    script = Path(store.__file__)
    def call(*parts):
        result = subprocess.run([sys.executable, str(script), *map(str, parts)], capture_output=True, text=True)
        return result.returncode, json.loads(result.stdout)
    code, result = call('publish', args['root'], args['source'], args['key'], args['category'], args['note'],
                        '--evidence', args['evidence'][0])
    assert code == 0 and result['ok']
    code, read = call('inspect', args['root'], result['data']['id'])
    assert code == 0 and read['data']['artifact_verified']
    code, found = call('lookup', args['root'], args['source'], args['key'])
    assert code == 0 and len(found['data']['analyzed']) == 1
    code, failure = call('inspect', args['root'], 'invalid')
    assert code == 6 and failure['error']['retryable'] is False


def test_receipt_path_traversal_rejected_before_read(tmp_path):
    args = fixture(tmp_path)
    result = store.publish(**args)
    receipt = args['root'] / '.triage' / (result['id'] + '.json')
    record = json.loads(receipt.read_text())
    record['note'] = '../outside.md'
    receipt.write_bytes(store.encoded(record))
    with pytest.raises(ValueError, match='note path'):
        store.inspect(args['root'], result['id'])


def test_changed_receipt_never_reports_complete(tmp_path):
    args = fixture(tmp_path)
    result = store.publish(**args)
    receipt = args['root'] / '.triage' / (result['id'] + '.json')
    record = json.loads(receipt.read_text())
    record['evidence'] = [{'path': str(tmp_path / 'never-read'), 'sha256': 'x'}]
    receipt.write_bytes(store.encoded(record))
    assert store.inspect(args['root'], result['id'])['artifact_verified'] is False


def test_note_size_bound_precedes_output(tmp_path):
    args = fixture(tmp_path)
    args['note'].write_bytes(b'x' * (4 * 1024 * 1024 + 1))
    with pytest.raises(ValueError, match='4 MiB'):
        store.publish(**args)
    assert not args['root'].exists()


@pytest.mark.parametrize('author', ["'O''Neil'", '"O\'Neil"'])
def test_valid_quoted_author_is_preserved(tmp_path, author):
    args = fixture(tmp_path)
    args['note'].write_text(args['note'].read_text().replace('author: null', 'author: ' + author))
    result = store.publish(**args)
    text = Path(result['note']).read_text(encoding='utf-8')
    assert 'author: ' + author in text
    assert store.note_metadata(text)['author'] == "O'Neil"


def test_failed_sync_does_not_publish_partial_artifact(tmp_path, monkeypatch):
    target = tmp_path / 'receipt.json'
    def fail(fd):
        raise OSError('synthetic sync failure')
    monkeypatch.setattr(store.os, 'fsync', fail)
    with pytest.raises(OSError):
        store.exclusive(target, b'{"complete":true}')
    assert not target.exists()


def test_crashed_process_releases_lock(tmp_path):
    args = fixture(tmp_path)
    child = subprocess.run([sys.executable, '-c',
        'import sys,os; sys.path.insert(0,sys.argv[1]); import triage_store as s; '
        'lock=s.locked(sys.argv[2]); lock.__enter__(); os._exit(7)',
        str(Path(store.__file__).parent), str(args['root'])],
        timeout=10, capture_output=True,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0)
    assert child.returncode == 7
    assert store.publish(**args)['artifact_verified']


def test_symlink_evidence_is_rejected(tmp_path):
    args = fixture(tmp_path)
    link = tmp_path / 'link.txt'
    try:
        link.symlink_to(args['evidence'][0])
    except OSError:
        pytest.skip('symlink creation unavailable')
    args['evidence'] = [link]
    with pytest.raises(ValueError, match='links'):
        store.publish(**args)
    assert not args['root'].exists()
