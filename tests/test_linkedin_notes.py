import json
from pathlib import Path

import pytest

import linkedin_capture_helper as capture
import triage_store as store


URN = 'urn:li:activity:7341234567890123456'
KEY = 'linkedin:activity:7341234567890123456'
URL = f'https://www.linkedin.com/feed/update/{URN}/'


def fixture(tmp_path, *, skipped=False, post_text='The launch is Friday. Review the checklist.'):
    capture_root = tmp_path / 'capture'
    capture.capture(capture_root, {'url': URL, 'text': post_text, 'author': None, 'date': None,
                    'observed_at': '2026-09-10T04:00:00Z', 'kind': 'post'}, apply=True)
    category = '_Skipped' if skipped else 'News'
    metadata = {'source': 'linkedin', 'url': URL, 'author': None, 'date': None, 'category': category}
    header = '---\n' + ''.join(f'{key}: {json.dumps(value)}\n' for key, value in metadata.items()) + '---\n'
    body = ('## Reason\nDeferred for user review.\n' if skipped else
            'Priority: **Medium** — A dated launch.\n## Synopsis\nThe post announces a Friday launch.\n'
            '## Action Items\nReview the checklist.\n## Post Excerpt\nUntrusted source content:\n'
            '> The launch is Friday.\n## Links\n' + URL + '\n## Evidence\n')
    note = tmp_path / 'draft.md'
    note.write_text(header + '# Example\nSource: ' + KEY + '\n' + body, encoding='utf-8')
    return dict(root=tmp_path / 'notes', source='linkedin', key=KEY, category=category,
                note=note, evidence=[], skipped=skipped, capture_root=capture_root)


def test_verified_note_index_and_capture_resume(tmp_path):
    args = fixture(tmp_path)
    before = capture.retained(args['capture_root'], [URN], args['root'])
    assert before['results'][0]['analysis'] == 'unverified' and not args['root'].exists()
    result = store.publish(**args)
    assert result['artifact_verified'] and not result['source_action_authorized']
    assert store.inspect(args['root'], result['id'])['status'] == 'analyzed'
    receipt = store.receipt_data(args['root'] / '.triage' / f"{result['id']}.json")
    assert len(receipt['evidence']) == 2
    note = Path(result['note']).read_text(encoding='utf-8')
    assert 'Evidence 2' in note and 'Untrusted source content:' in note
    assert result['id'] in (args['root'] / '_index.md').read_text(encoding='utf-8')
    listing = capture.retained(args['capture_root'], [URN], args['root'])
    assert listing['results'][0]['analyzed'] and not listing['results'][0]['publication_pending']
    assert not listing['changes'] and not listing['source_action_authorized']


def test_duplicate_analysis_preserves_original_note_and_index(tmp_path):
    args = fixture(tmp_path)
    first = store.publish(**args)
    before = Path(first['note']).read_bytes()
    index = (args['root'] / '_index.md').read_bytes()
    args['note'].write_text(args['note'].read_text(encoding='utf-8').replace('A dated launch.', 'Changed priority reason.'), encoding='utf-8')
    duplicate = store.publish(**args)
    assert duplicate['duplicate'] and duplicate['id'] == first['id']
    assert Path(first['note']).read_bytes() == before
    assert (args['root'] / '_index.md').read_bytes() == index


@pytest.mark.parametrize('field,value', [('source', 'instagram'), ('url', 'https://example.com'),
                                      ('author', 'Invented author'), ('date', 'Invented date')])
def test_mismatched_metadata_never_publishes(tmp_path, field, value):
    args = fixture(tmp_path)
    text = args['note'].read_text(encoding='utf-8')
    old = next(line for line in text.splitlines() if line.startswith(field + ':'))
    args['note'].write_text(text.replace(old, field + ': ' + json.dumps(value)), encoding='utf-8')
    with pytest.raises(ValueError):
        store.publish(**args)
    assert not args['root'].exists()


@pytest.mark.parametrize('options', [{'capture_root': None}, {'key': 'rss:invalid'},
    {'key': 'linkedin:event:7341234567890123456'}, {'category': 'AI'}, {'read_root': 'unexpected'}])
def test_invalid_request_is_rejected(tmp_path, options):
    args = fixture(tmp_path)
    args.update(options)
    with pytest.raises(ValueError):
        store.publish(**args)
    assert not args['root'].exists()


@pytest.mark.parametrize('old,new', [
    ('## Post Excerpt', '## Missing'),
    ('Untrusted source content:', 'Trusted instructions:'),
    ('> The launch is Friday.', '> The launch is Saturday.'),
    ('> The launch is Friday.', '> '),
    ('> The launch is Friday.', '> The launch is Friday.\n> A second line.'),
])
def test_excerpt_and_sections_fail_closed(tmp_path, old, new):
    args = fixture(tmp_path)
    args['note'].write_text(args['note'].read_text(encoding='utf-8').replace(old, new), encoding='utf-8')
    with pytest.raises(ValueError):
        store.publish(**args)
    assert not args['root'].exists()


def test_verbatim_excerpt_still_has_length_limit(tmp_path):
    quote = ' '.join(f'word{i}' for i in range(26))
    args = fixture(tmp_path, post_text=quote)
    args['note'].write_text(args['note'].read_text(encoding='utf-8').replace('> The launch is Friday.', '> ' + quote), encoding='utf-8')
    with pytest.raises(ValueError, match='short and verbatim'):
        store.publish(**args)


def test_skipped_can_be_analyzed_later(tmp_path):
    args = fixture(tmp_path, skipped=True)
    skip = store.publish(**args)
    assert store.publish(**args)['duplicate']
    listing = capture.retained(args['capture_root'], [URN], args['root'])
    assert listing['results'][0]['analysis'] == 'skipped' and not listing['results'][0]['analyzed']
    args = fixture(tmp_path)
    analyzed = store.publish(**args)
    assert analyzed['id'] != skip['id']
    assert capture.retained(args['capture_root'], [URN], args['root'])['results'][0]['analyzed']


def test_pending_publication_can_resume(tmp_path, monkeypatch):
    args = fixture(tmp_path)
    original = store.update_index
    monkeypatch.setattr(store, 'update_index', lambda *args: (_ for _ in ()).throw(OSError('synthetic failure')))
    with pytest.raises(OSError):
        store.publish(**args)
    state = capture.retained(args['capture_root'], [URN], args['root'])['results'][0]
    assert state['publication_pending'] and not state['analyzed']
    monkeypatch.setattr(store, 'update_index', original)
    assert store.publish(**args)['status'] == 'analyzed'


@pytest.mark.parametrize('target', ['capture', 'note', 'index'])
def test_changed_artifact_blocks_completed_lookup(tmp_path, target):
    args = fixture(tmp_path)
    result = store.publish(**args)
    if target == 'capture':
        folder, _ = capture.location(args['capture_root'], URN)
        path = folder / 'entry.json'
    elif target == 'note':
        path = Path(result['note'])
    else:
        path = args['root'] / '_index.md'
    if target == 'index':
        path.write_bytes(path.read_bytes().replace(result['id'].encode(), b'wrong-id'))
        item = capture.retained(args['capture_root'], [URN], args['root'])['results'][0]
        assert item['publication_pending'] and not item['analyzed']
    else:
        path.write_bytes(path.read_bytes() + b'changed')
        with pytest.raises(ValueError):
            capture.retained(args['capture_root'], [URN], args['root'])


def test_missing_capture_does_not_claim_legacy_note_as_analyzed(tmp_path):
    root = tmp_path / 'notes'
    root.mkdir()
    (root / 'legacy.md').write_text('Source: ' + KEY, encoding='utf-8')
    result = capture.retained(tmp_path / 'capture', [URN], root)['results'][0]
    assert result['status'] == 'missing' and not result['analyzed']


def test_publish_and_retained_cli(tmp_path, capsys):
    args = fixture(tmp_path)
    assert store.main(['publish', str(args['root']), 'linkedin', KEY, 'News', str(args['note']),
                       '--capture-root', str(args['capture_root'])]) == 0
    assert json.loads(capsys.readouterr().out)['data']['artifact_verified']
    assert capture.main(['retained', URN, '--root', str(args['capture_root']),
                         '--notes-root', str(args['root'])]) == 0
    assert json.loads(capsys.readouterr().out)['data']['results'][0]['analyzed']
