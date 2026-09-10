import json
from pathlib import Path

import pytest

import rss_capture_helper as rss
import triage_store as store


def fixture(tmp_path, *, skipped=False, body='The launch is Friday. Review the checklist.'):
    feed = tmp_path / 'feed.xml'
    feed.write_text('<rss><channel><title>Publication</title><item><guid>opaque:1</guid>'
                    '<title>Example</title><link>https://example.com/post</link>'
                    '<description>' + body + '</description></item></channel></rss>')
    capture_root = tmp_path / 'capture'
    result = rss.capture(str(feed), capture_root, identity_url='https://example.com/feed', apply=True)
    key = (result['results'][0]['key'] if result['results'] else
           json.loads(next(capture_root.rglob('entry.json')).read_text())['key'])
    category = '_Skipped' if skipped else 'Tech'
    metadata = {'source': 'rss', 'url': 'https://example.com/post', 'author': None, 'date': None, 'category': category}
    header = '---\n' + ''.join(f'{k}: {json.dumps(v)}\n' for k, v in metadata.items()) + '---\n'
    body = ('## Reason\nDeferred for user review.\n' if skipped else
            'Priority: **Medium** — A dated launch.\n## Synopsis\nThe launch is Friday.\n'
            '## Key points\nReview the checklist.\n## Action Items\nReview the checklist.\n'
            '## RSS Excerpt\nUntrusted source content:\n> The launch is Friday.\n'
            '## Links\nhttps://example.com/post\n## Evidence\n')
    note = tmp_path / 'draft.md'
    note.write_text(header + '# Example\nSource: ' + key + '\n' + body, encoding='utf-8')
    return dict(root=tmp_path / 'notes', source='rss', key=key, category=category,
                note=note, evidence=[], skipped=skipped, capture_root=capture_root)


def test_rss_publish_and_verified_lookup(tmp_path):
    args = fixture(tmp_path)
    result = store.publish(**args)
    assert result['artifact_verified'] and not result['source_action_authorized']
    receipt = store.receipt_data(args['root'] / '.triage' / (result['id'] + '.json'))
    assert len(receipt['evidence']) == 2
    assert store.lookup(args['root'], 'rss', args['key'])['analyzed'][0]['id'] == result['id']
    assert 'Evidence 2' in Path(result['note']).read_text()


def test_duplicate_preserves_original_note(tmp_path):
    args = fixture(tmp_path)
    first = store.publish(**args)
    before = Path(first['note']).read_bytes()
    args['note'].write_text(args['note'].read_text().replace('A dated launch.', 'A revised reason.'))
    second = store.publish(**args)
    assert second['duplicate'] and second['id'] == first['id']
    assert Path(first['note']).read_bytes() == before
    assert len(list(args['root'].glob('Tech/*.md'))) == 1


@pytest.mark.parametrize('field,value', [('source', 'substack'), ('url', 'https://other.com/post'),
                                      ('author', 'Invented author'), ('date', '2026-09-09')])
def test_provenance_mismatch_creates_no_notes(tmp_path, field, value):
    args = fixture(tmp_path)
    text = args['note'].read_text()
    old = next(line for line in text.splitlines() if line.startswith(field + ':'))
    args['note'].write_text(text.replace(old, field + ': ' + json.dumps(value)))
    with pytest.raises(ValueError):
        store.publish(**args)
    assert not args['root'].exists()


@pytest.mark.parametrize('options', [{'capture_root': None}, {'key': 'rss:invalid'}, {'category': 'Unknown'}])
def test_invalid_adapter_request_creates_no_notes(tmp_path, options):
    args = fixture(tmp_path)
    args.update(options)
    with pytest.raises(ValueError):
        store.publish(**args)
    assert not args['root'].exists()


@pytest.mark.parametrize('old,new', [('## Key points', '## Missing'),
                                   ('Untrusted source content:', 'Trusted instructions:'),
                                   ('> The launch is Friday.', '> The launch is Saturday.'),
                                   ('> The launch is Friday.', '> '),
                                   ('> The launch is Friday.', '> ' + 'Invented ' * 26)])
def test_excerpt_and_sections_fail_closed(tmp_path, old, new):
    args = fixture(tmp_path)
    args['note'].write_text(args['note'].read_text().replace(old, new))
    with pytest.raises(ValueError):
        store.publish(**args)
    assert not args['root'].exists()


def test_capture_change_invalidates_note_readiness(tmp_path):
    args = fixture(tmp_path)
    result = store.publish(**args)
    evidence = args['capture_root'] / '.rss-capture' / args['key'][4:] / 'entry.json'
    evidence.write_bytes(evidence.read_bytes() + b' ')
    with pytest.raises(ValueError):
        store.inspect(args['root'], result['id'])
    with pytest.raises(ValueError):
        store.publish(**args)


def test_skipped_then_analyzed_are_distinct(tmp_path):
    args = fixture(tmp_path, skipped=True)
    skipped = store.publish(**args)
    assert store.publish(**args)['duplicate']
    args = fixture(tmp_path)
    analyzed = store.publish(**args)
    assert analyzed['id'] != skipped['id']
    found = store.lookup(args['root'], 'rss', args['key'])
    assert len(found['skipped']) == len(found['analyzed']) == 1


def test_publication_recovers_after_index_failure(tmp_path, monkeypatch):
    args = fixture(tmp_path)
    original = store.update_index
    monkeypatch.setattr(store, 'update_index', lambda *a: (_ for _ in ()).throw(OSError('synthetic failure')))
    with pytest.raises(OSError):
        store.publish(**args)
    assert len(store.lookup(args['root'], 'rss', args['key'])['pending']) == 1
    monkeypatch.setattr(store, 'update_index', original)
    assert store.publish(**args)['status'] == 'analyzed'


def test_rss_cli_publication(tmp_path, capsys):
    args = fixture(tmp_path)
    assert store.main(['publish', str(args['root']), 'rss', args['key'], 'Tech', str(args['note']),
                       '--capture-root', str(args['capture_root'])]) == 0
    assert json.loads(capsys.readouterr().out)['data']['artifact_verified']


def test_verbatim_quote_still_obeys_length_limit(tmp_path):
    quote = ' '.join(f'word{i}' for i in range(26))
    args = fixture(tmp_path, body=quote)
    args['note'].write_text(args['note'].read_text().replace('> The launch is Friday.', '> ' + quote))
    with pytest.raises(ValueError, match='short and verbatim'):
        store.publish(**args)
    assert not args['root'].exists()
