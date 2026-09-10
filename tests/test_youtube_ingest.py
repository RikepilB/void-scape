import copy
import json

import pytest

import youtube_ingest_helper as ingest


URL = 'https://www.youtube.com/watch?v=abcdefghijk'


def snapshot():
    entry = {'key': 'youtube:abcdefghijk', 'url': URL, 'title': 'Example',
             'author': None, 'date': None, 'availability': None}
    return {'schema': 1, 'selection': {'kind': 'playlist', 'key': None,
            'url': 'https://www.youtube.com/playlist?list=PLabcdefghijk'},
            'entries': [entry], 'start': 1, 'limit': 2, 'unresolved': 0, 'content_trust': 'untrusted'}


def test_preview_has_no_files_and_capture_is_not_analysis(tmp_path):
    record = snapshot()
    preview = ingest.process_snapshot(tmp_path, record)
    assert preview['results'][0]['status'] == 'new' and not preview['changes']
    assert list(tmp_path.iterdir()) == []
    result = ingest.process_snapshot(tmp_path, record, apply=True)
    assert result['results'][0]['status'] == 'captured' and result['analyzed'] == 0
    assert ingest.verify(tmp_path, 'youtube:abcdefghijk') == record['entries'][0]
    assert ingest.read_snapshot(tmp_path, result['snapshot']) == record


def test_cross_playlist_duplicate_preserves_first_evidence(tmp_path):
    record = snapshot()
    ingest.process_snapshot(tmp_path, record, apply=True)
    original = ingest.verify(tmp_path, 'youtube:abcdefghijk')
    record['selection']['url'] = 'https://www.youtube.com/playlist?list=PLmnopqrstuv'
    record['entries'][0]['title'] = 'Changed'
    result = ingest.process_snapshot(tmp_path, record, apply=True)
    assert result['results'][0]['status'] == 'duplicate'
    assert result['results'][0]['metadata_changed']
    assert ingest.verify(tmp_path, 'youtube:abcdefghijk') == original
    assert ingest.read_snapshot(tmp_path, result['snapshot'])['entries'][0]['title'] == 'Changed'


def test_resume_uses_original_selection_without_network(tmp_path, monkeypatch):
    record = snapshot()
    result = ingest.process_snapshot(tmp_path, record, apply=True)
    monkeypatch.setattr(ingest, 'discover', lambda *a, **k: pytest.fail('network'))
    before = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    retained = ingest.retained(tmp_path, result['snapshot'], tmp_path / 'notes')
    assert retained['results'][0]['key'] == 'youtube:abcdefghijk'
    assert not retained['changes']
    assert before == {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}


def test_failed_capture_keeps_snapshot_for_exact_recovery(tmp_path, monkeypatch):
    record = snapshot()
    original = ingest.exclusive
    def fail_marker(path, data):
        if path.name == 'captured.json':
            raise OSError('synthetic sync failure')
        original(path, data)
    monkeypatch.setattr(ingest, 'exclusive', fail_marker)
    with pytest.raises(OSError):
        ingest.process_snapshot(tmp_path, record, apply=True)
    identity = ingest.digest(ingest.encoded(record))
    retained = ingest.retained(tmp_path, identity, tmp_path / 'notes')
    assert retained['incomplete'] == 1 and retained['results'] == []
    monkeypatch.setattr(ingest, 'exclusive', original)
    recovered = ingest.process_snapshot(tmp_path, ingest.read_snapshot(tmp_path, identity), apply=True)
    assert recovered['results'][0]['status'] == 'captured'


def test_capture_failure_cannot_be_recovered_with_changed_payload(tmp_path, monkeypatch):
    record = snapshot()
    original = ingest.exclusive
    def fail_marker(path, data):
        if path.name == 'captured.json':
            raise OSError('synthetic failure')
        original(path, data)
    monkeypatch.setattr(ingest, 'exclusive', fail_marker)
    with pytest.raises(OSError):
        ingest.process_snapshot(tmp_path, record, apply=True)
    monkeypatch.setattr(ingest, 'exclusive', original)
    record['entries'][0]['title'] = 'Changed'
    with pytest.raises(ValueError, match='refusing overwrite'):
        ingest.process_snapshot(tmp_path, record, apply=True)


@pytest.mark.parametrize('target', ['entry.json', 'captured.json'])
def test_tampered_capture_blocks_duplicates_and_analysis(tmp_path, target):
    result = ingest.process_snapshot(tmp_path, snapshot(), apply=True)
    path = tmp_path / '.youtube-capture/videos/abcdefghijk' / target
    path.write_text('{}')
    with pytest.raises((ValueError, KeyError)):
        ingest.process_snapshot(tmp_path, snapshot())
    with pytest.raises((ValueError, KeyError)):
        ingest.retained(tmp_path, result['snapshot'], tmp_path / 'notes')


def test_tampered_snapshot_cannot_change_selected_scope(tmp_path):
    result = ingest.process_snapshot(tmp_path, snapshot(), apply=True)
    path = tmp_path / '.youtube-capture/selections' / (result['snapshot'] + '.json')
    record = snapshot()
    record['start'] = 2
    path.write_bytes(ingest.encoded(record))
    with pytest.raises(ValueError, match='selection changed'):
        ingest.read_snapshot(tmp_path, result['snapshot'])


@pytest.mark.parametrize('state,count', [('analyzed', 'analyzed'), ('skipped', 'skipped'), ('pending', None)])
def test_retained_note_states_are_distinct(tmp_path, monkeypatch, state, count):
    result = ingest.process_snapshot(tmp_path, snapshot(), apply=True)
    def lookup(*args):
        data = {'analyzed': [], 'skipped': [], 'pending': []}
        data[state] = [{'id': 'synthetic'}]
        return data
    monkeypatch.setattr(ingest, 'lookup', lookup)
    retained = ingest.retained(tmp_path, result['snapshot'], tmp_path / 'notes')
    if count:
        assert retained[count] == 1 and retained['results'] == []
    else:
        assert retained['results'][0]['publication_pending']


@pytest.mark.parametrize('field,value', [('limit', 0), ('start', True), ('unresolved', 3),
                                      ('content_trust', 'trusted'), ('schema', 2)])
def test_snapshot_validation_precedes_writes(tmp_path, field, value):
    record = snapshot()
    record[field] = value
    with pytest.raises(ValueError):
        ingest.process_snapshot(tmp_path, record, apply=True)
    assert list(tmp_path.iterdir()) == []


def test_duplicate_and_noncanonical_entries_are_rejected(tmp_path):
    record = snapshot()
    record['entries'].append(copy.deepcopy(record['entries'][0]))
    with pytest.raises(ValueError, match='duplicate'):
        ingest.process_snapshot(tmp_path, record)
    record = snapshot()
    record['entries'][0]['url'] = 'https://youtu.be/abcdefghijk'
    with pytest.raises(ValueError, match='identity'):
        ingest.process_snapshot(tmp_path, record)


def test_cli_dry_run_capture_retained_resume_and_error(tmp_path, capsys):
    root = str(tmp_path)
    assert ingest.main(['capture', URL, '--root', root]) == 0
    assert json.loads(capsys.readouterr().out)['data']['mode'] == 'preview'
    assert list(tmp_path.iterdir()) == []
    assert ingest.main(['capture', URL, '--root', root, '--apply']) == 0
    identity = json.loads(capsys.readouterr().out)['data']['snapshot']
    assert ingest.main(['retained', '--root', root, '--snapshot', identity, '--notes-root', str(tmp_path / 'notes')]) == 0
    assert json.loads(capsys.readouterr().out)['data']['results'][0]['status'] == 'needs_note'
    assert ingest.main(['resume', '--root', root, '--snapshot', identity, '--apply']) == 0
    assert json.loads(capsys.readouterr().out)['data']['results'][0]['status'] == 'duplicate'
    assert ingest.main(['resume', '--root', root, '--snapshot', '../outside']) == 6
    assert not json.loads(capsys.readouterr().out)['ok']


def test_cli_missing_fetch_permission_is_distinct(tmp_path, capsys):
    assert ingest.main(['capture', snapshot()['selection']['url'], '--root', str(tmp_path)]) == 4
    assert json.loads(capsys.readouterr().out)['error']['code'] == 'fetch_approval_required'
    assert list(tmp_path.iterdir()) == []


def test_project_youtube_mirrors_match():
    from sync_youtube_skill import ROOT, rendered_files
    for path, content in rendered_files(ROOT).items():
        assert path.read_text(encoding='utf-8') == content, path
