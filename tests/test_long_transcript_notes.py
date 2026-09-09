import json

import pytest

import local_notes as notes
from test_local_notes import service


def long_text():
    return ''.join(f'[{number:02}:00] Segment {number}: ' + 'Detailed evidence. ' * 100 + '\n'
                   for number in range(8))


def fake_author(text, model, **kwargs):
    timestamp, lines = next(iter(notes.transcript_lines(text).items()))
    return {'title': 'Segment notes', 'synopsis': lines[0][:100], 'priority': 'Medium',
            'action_items': [{'text': 'Review this segment.', 'quote': lines[0][:80], 'timestamp': timestamp}],
            'key_moments': [{'text': 'Segment evidence.', 'quote': lines[0][:80], 'timestamp': timestamp}]}


def fake_overview(text, model, **kwargs):
    assert len(text.encode('utf-8')) <= notes.MAX_TRANSCRIPT
    return {'title': 'Recording overview', 'synopsis': 'This recording covers the retained segment summaries.'}


def test_very_long_unicode_line_preserves_every_character_and_timestamp():
    body = '東京 café 🧪 evidence ' * 600
    pieces = notes.chunks('[00:04] ' + body + '\n')
    assert len(pieces) > 1
    assert all(len(piece.encode('utf-8')) <= notes.MAX_TRANSCRIPT for piece in pieces)
    recovered = ''.join(line[len('[00:04] '):] for piece in pieces for line in piece.splitlines())
    assert recovered == body
    assert all(line.startswith('[00:04] ') for piece in pieces for line in piece.splitlines())


def test_unstamped_tail_is_rejected_before_generation(monkeypatch):
    monkeypatch.setattr(notes, 'author', lambda *a, **kw: pytest.fail('generation must not start'))
    with pytest.raises(notes.LocalNoteError, match='every transcript line'):
        notes.author_document(long_text() + 'unattributed tail', 'local')


def test_long_document_keeps_late_actions_and_full_transcript(monkeypatch):
    monkeypatch.setattr(notes, 'author', fake_author)
    monkeypatch.setattr(notes, 'overview', fake_overview)
    text = long_text()
    value, count = notes.author_document(text, 'local')
    assert count > 1
    assert any(item['timestamp'] == '06:00' for item in value['action_items'])
    result = notes.render(value, text, 'recording', 'local', segments=count)
    assert all('    ' + line in result for line in text.splitlines())
    assert result.count('## Full Transcript') == 1


def test_interrupted_generation_reuses_verified_chunks(tmp_path, monkeypatch):
    calls = []
    def interrupted(text, model, **kwargs):
        calls.append(text)
        if len(calls) == 2:
            raise notes.LocalNoteError('synthetic interruption')
        return fake_author(text, model)
    monkeypatch.setattr(notes, 'author', interrupted)
    monkeypatch.setattr(notes, 'overview', fake_overview)
    text = long_text()
    cache = tmp_path / 'cache'
    with pytest.raises(notes.LocalNoteError, match='interruption'):
        notes.author_document(text, 'local', cache=cache)
    assert len(list(cache.glob('*.json'))) == 1
    first = calls[0]
    calls.clear()
    def resumed(text, model, **kwargs):
        calls.append(text)
        return fake_author(text, model)
    monkeypatch.setattr(notes, 'author', resumed)
    value, _ = notes.author_document(text, 'local', cache=cache)
    assert first not in calls
    assert value['key_moments']
    calls.clear()
    notes.author_document(text, 'local', cache=cache)
    assert calls == []


def test_changed_checkpoint_is_preserved_and_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(notes, 'author', fake_author)
    monkeypatch.setattr(notes, 'overview', fake_overview)
    text = '[00:00] Retained source.\n'
    notes.author_document(text, 'local', cache=tmp_path)
    path = next(tmp_path.glob('*.json'))
    record = json.loads(path.read_text(encoding='utf-8'))
    record['value']['synopsis'] = 'Changed content'
    changed = json.dumps(record)
    path.write_text(changed, encoding='utf-8')
    with pytest.raises(notes.LocalNoteError, match='content changed'):
        notes.author_document(text, 'local', cache=tmp_path)
    assert path.read_text(encoding='utf-8') == changed


def test_reduction_requests_stay_bounded(monkeypatch):
    monkeypatch.setattr(notes, 'author', fake_author)
    def verbose(text, model, **kwargs):
        value = fake_author(text, model)
        value['synopsis'] = '多言語要約' * 300
        return value
    requests = []
    def reduce(text, model, **kwargs):
        requests.append(text)
        return fake_overview(text, model)
    monkeypatch.setattr(notes, 'author', verbose)
    monkeypatch.setattr(notes, 'overview', reduce)
    value, _ = notes.author_document(long_text(), 'local')
    assert len(requests) > 1
    assert value['synopsis']


def test_source_change_uses_new_chunk_identity(tmp_path, monkeypatch):
    calls = []
    def generate(text, model, **kwargs):
        calls.append(text)
        return fake_author(text, model)
    monkeypatch.setattr(notes, 'author', generate)
    notes.author_document('[00:00] Original text.\n', 'local', cache=tmp_path)
    notes.author_document('[00:00] Revised text.\n', 'local', cache=tmp_path)
    assert len(calls) == 2


def test_overview_rechecks_cloud_permission_before_transfer():
    call, calls = service({'/api/status': {'cloud': {'disabled': False}}})
    with pytest.raises(notes.LocalNoteError, match='disable cloud'):
        notes.overview('Private segment synopsis.', 'gemma3:4b', call=call)
    assert all(path != '/api/generate' for path, _ in calls)


@pytest.mark.parametrize('synopsis', ['A' * 601, 'Two\nparagraphs'], ids=['oversized', 'control-character'])
def test_overview_rejects_invalid_generated_text(synopsis):
    call, _ = service({'/api/generate': {'done': True, 'done_reason': 'stop',
                       'response': json.dumps({'title': 'Overview', 'synopsis': synopsis})}})
    with pytest.raises(notes.LocalNoteError, match='generated note field'):
        notes.overview('Retained summaries.', 'gemma3:4b', call=call)


def test_failed_overview_resumes_without_regenerating_segments(tmp_path, monkeypatch):
    monkeypatch.setattr(notes, 'author', fake_author)
    def fail(*args, **kwargs):
        raise notes.LocalNoteError('invalid overview')
    monkeypatch.setattr(notes, 'overview', fail)
    with pytest.raises(notes.LocalNoteError, match='invalid overview'):
        notes.author_document(long_text(), 'local', cache=tmp_path)
    monkeypatch.setattr(notes, 'author', lambda *a, **kw: pytest.fail('segment was already cached'))
    monkeypatch.setattr(notes, 'overview', fake_overview)
    value, count = notes.author_document(long_text(), 'local', cache=tmp_path)
    assert count > 1 and value['action_items']
