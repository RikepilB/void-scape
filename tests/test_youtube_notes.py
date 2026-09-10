import json
from pathlib import Path

import pytest

import triage_store as store
import youtube_ingest_helper as ingest
import youtube_read as reader
from test_youtube_read import fixture as reader_fixture


def fixture(tmp_path, *, skipped=False, visual=False):
    capture, work, calls, invoke = reader_fixture(tmp_path, visual=visual)
    if not skipped:
        reader.prepare(capture, 'youtube:abcdefghijk', work, tier='visual' if visual else 'both', reader=invoke)
    category = '_Skipped' if skipped else 'Tech'
    metadata = {'source': 'youtube', 'url': 'https://www.youtube.com/watch?v=abcdefghijk',
                'author': None, 'date': None, 'category': category}
    header = '---\n' + ''.join(f'{key}: {json.dumps(value)}\n' for key, value in metadata.items()) + '---\n'
    body = ('## Reason\nDeferred for user review.\n' if skipped else
            'Priority: **Medium** — Example evidence.\n## Synopsis\nA synthetic example.\n'
            '## Action Items\nNone identified.\n## Key moments\n'
            '- [00:02] A synthetic frame.\n## Links\nhttps://www.youtube.com/watch?v=abcdefghijk\n## Evidence\n')
    note = tmp_path / 'draft.md'
    note.write_text(header + '# Example\nSource: youtube:abcdefghijk\n' + body, encoding='utf-8')
    return {'root': tmp_path / 'notes', 'source': 'youtube', 'key': 'youtube:abcdefghijk',
            'category': category, 'note': note, 'evidence': [], 'capture_root': capture,
            'read_root': None if skipped else work, 'skipped': skipped}


@pytest.mark.parametrize('visual', [False, True])
def test_publish_with_actual_reader_citation_and_resume(tmp_path, visual):
    args = fixture(tmp_path, visual=visual)
    result = store.publish(**args)
    assert result['artifact_verified'] and not result['source_action_authorized']
    assert store.lookup(args['root'], 'youtube', args['key'])['analyzed']
    snapshots = list((args['capture_root'] / '.youtube-capture/selections').glob('*.json'))
    pending = ingest.retained(args['capture_root'], snapshots[0].stem, args['root'])
    assert pending['analyzed'] == 1 and pending['results'] == []
    before = Path(result['note']).read_bytes()
    args['note'].write_text(args['note'].read_text().replace('Example evidence.', 'Changed reason.'))
    duplicate = store.publish(**args)
    assert duplicate['duplicate'] and Path(result['note']).read_bytes() == before


def test_transcript_timestamp_is_supported(tmp_path):
    args = fixture(tmp_path)
    args['note'].write_text(args['note'].read_text().replace('[00:02]', '[00:04]'))
    assert store.publish(**args)['artifact_verified']


@pytest.mark.parametrize('change', ['timestamp', 'missing_read', 'wrong_key', 'changed_transcript', 'changed_author'])
def test_false_provenance_cannot_publish(tmp_path, change):
    args = fixture(tmp_path)
    if change == 'timestamp':
        args['note'].write_text(args['note'].read_text().replace('[00:02]', '[09:59]'))
    elif change == 'missing_read':
        args['read_root'] = None
    elif change == 'wrong_key':
        args['key'] = 'youtube:lmnopqrstuv'
    elif change == 'changed_transcript':
        (args['read_root'] / 'evidence/transcript.txt').write_text('changed')
    else:
        args['note'].write_text(args['note'].read_text().replace('author: null', 'author: "Invented"'))
    with pytest.raises((ValueError, OSError, KeyError)):
        store.publish(**args)
    assert not args['root'].exists()


def test_skip_is_separate_and_keeps_capture_evidence(tmp_path):
    args = fixture(tmp_path, skipped=True)
    result = store.publish(**args)
    assert result['status'] == 'skipped'
    assert store.lookup(args['root'], 'youtube', args['key'])['analyzed'] == []
    receipt = store.receipt_data(args['root'] / '.triage' / (result['id'] + '.json'))
    assert len(receipt['evidence']) == 2
