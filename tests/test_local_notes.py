import copy
import json

import pytest

import local_notes as notes


TRANSCRIPT = '[00:00] Maya will send the checklist Friday.\n[00:04] Launch remains undecided.\n'
NOTE = {'title': 'Checklist review', 'synopsis': 'Maya will send a checklist; launch remains undecided.',
        'priority': 'Medium', 'action_items': [{'text': 'Maya: send the checklist Friday.',
        'timestamp': '00:00', 'quote': 'Maya will send the checklist Friday.'}],
        'key_moments': [{'text': 'No launch decision yet.', 'timestamp': '00:04',
                         'quote': 'Launch remains undecided.'}]}


def service(overrides=None):
    values = {'/api/status': {'cloud': {'disabled': True}},
              '/api/tags': {'models': [{'name': 'gemma3:4b', 'size': 123}]},
              '/api/show': {'model_info': {'general.architecture': 'gemma3'}, 'capabilities': ['completion']},
              '/api/generate': {'done': True, 'done_reason': 'stop', 'response': json.dumps(NOTE)}}
    values.update(overrides or {})
    calls = []
    def call(path, payload=None):
        calls.append((path, payload))
        return values[path]
    return call, calls


@pytest.mark.parametrize('override', [
    {'/api/status': {}}, {'/api/status': {'cloud': {'disabled': False}}},
    {'/api/status': {'cloud': {'disabled': 'true'}}},
    {'/api/tags': {'models': []}},
    {'/api/tags': {'models': [{'name': 'gemma3:4b', 'size': 123, 'remote_host': 'https://remote.invalid'}]}},
    {'/api/show': {'remote_model': 'remote', 'model_info': {}, 'capabilities': ['completion']}},
])
def test_failed_preflight_never_sends_transcript(override):
    call, calls = service(override)
    with pytest.raises(notes.LocalNoteError):
        notes.author(TRANSCRIPT, 'gemma3:4b', call=call)
    assert all(path != '/api/generate' for path, _ in calls)
    assert TRANSCRIPT not in json.dumps(calls)


def test_local_author_requires_complete_generation():
    call, calls = service({'/api/generate': {'done': True, 'done_reason': 'length', 'response': json.dumps(NOTE)}})
    with pytest.raises(notes.LocalNoteError, match='complete'):
        notes.author(TRANSCRIPT, 'gemma3:4b', call=call)


@pytest.mark.parametrize('field,value', [('timestamp', '00:99'), ('quote', 'Maya approved launch.')])
def test_fabricated_citations_are_rejected(field, value):
    generated = copy.deepcopy(NOTE)
    generated['action_items'][0][field] = value
    with pytest.raises(notes.LocalNoteError, match='citation'):
        notes.validate_note(generated, TRANSCRIPT)


def test_valid_local_output_retains_full_transcript():
    call, calls = service()
    value = notes.author(TRANSCRIPT, 'gemma3:4b', call=call)
    rendered = notes.render(value, TRANSCRIPT, 'synthetic.mp4', 'gemma3:4b')
    assert '## Action Items' in rendered and '## Key moments' in rendered
    assert all('    ' + line in rendered for line in TRANSCRIPT.splitlines())
    assert calls[-1][1]['stream'] is False
    assert calls[-1][1]['keep_alive'] == 0


def test_long_transcript_never_contacts_runtime():
    call, calls = service()
    with pytest.raises(notes.LocalNoteError, match='chunking'):
        notes.author(TRANSCRIPT * 100, 'gemma3:4b', call=call)
    assert not calls


def test_existing_output_is_preserved(tmp_path):
    target = tmp_path / 'draft.md'
    target.write_text('existing')
    with pytest.raises(notes.LocalNoteError, match='already exists'):
        notes.draft(tmp_path, target, 'gemma3:4b')
    assert target.read_text() == 'existing'


def test_changed_transcript_does_not_publish(tmp_path, monkeypatch):
    transcript = tmp_path / 'transcript.txt'
    transcript.write_text(TRANSCRIPT)
    (tmp_path / 'manifest.json').write_text(json.dumps({'status': 'complete', 'backend': 'captions', 'transcript': str(transcript)}))
    def changed(*args, **kwargs):
        transcript.write_text('changed')
        return NOTE
    monkeypatch.setattr(notes, 'author', changed)
    output = tmp_path / 'output/note.md'
    with pytest.raises(notes.LocalNoteError, match='changed'):
        notes.draft(tmp_path, output, 'gemma3:4b')
    assert not output.parent.exists()


@pytest.mark.parametrize('status,body', [(302, b'{}'), (200, b'x' * (notes.MAX_RESPONSE + 1)), (200, b'[]')],
                         ids=['redirect', 'oversized', 'wrong-shape'])
def test_transport_is_loopback_bounded_and_does_not_follow_redirects(monkeypatch, status, body):
    calls = []
    class Response:
        def read(self, limit):
            assert limit == notes.MAX_RESPONSE + 1
            return body
    response = Response()
    response.status = status
    class Connection:
        def __init__(self, host, port, timeout):
            calls.append(host)
        def request(self, *args):
            pass
        def getresponse(self):
            return response
        def close(self):
            calls.append('closed')
    monkeypatch.setattr(notes.http.client, 'HTTPConnection', Connection)
    with pytest.raises(notes.LocalNoteError):
        notes.request('/api/status')
    assert calls == ['127.0.0.1', 'closed']
