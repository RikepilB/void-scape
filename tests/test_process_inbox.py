import json
import os
from pathlib import Path

import pytest

import process_inbox as inbox


@pytest.fixture
def roots(tmp_path):
    source, notes = tmp_path / 'inbox', tmp_path / 'notes'
    source.mkdir()
    return source, notes


def producer(source, work, model, backend, port):
    evidence = work / 'transcript.txt'
    evidence.write_text('[00:00] Maya will send the checklist Friday.\n')
    draft = work / 'draft.md'
    draft.write_text('# Review\n\n## Synopsis\nChecklist review.\n\n## Action Items\n'
                     '- [00:00] Maya: send the checklist Friday.\n\n## Key moments\n'
                     '- [00:00] Checklist plan.\n\n## Full Transcript\n    ' + evidence.read_text())
    return draft, [evidence]


def recording(root, name='recording.mp4', content=b'recording'):
    source = root / name
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(content)
    return source


def execute(root, notes, source, make=producer):
    return inbox.process_one(root, notes, source, 'cached', 'captions', 11434, producer=make)


def test_preview_is_oldest_first_and_writes_nothing(roots):
    root, notes = roots
    newer, older = recording(root, 'new.mp4'), recording(root, 'old.mp4')
    os.utime(older, (1, 1))
    recording(root, 'processed/previous.mp4')
    recording(root, '.inbox/work/internal.mp4')
    before = {str(path): path.stat().st_mtime_ns for path in root.rglob('*')}
    result = inbox.process(root, notes, 'cached', limit=1)
    assert result['selected'] == [str(older)] and result['changes'] is False
    assert before == {str(path): path.stat().st_mtime_ns for path in root.rglob('*')}
    assert not notes.exists()


def test_publish_verify_move_and_renamed_duplicate(roots):
    root, notes = roots
    source = recording(root)
    result = execute(root, notes, source)
    assert result['status'] == 'processed'
    assert not source.exists() and Path(result['note']).is_file()
    assert Path(result['processed']).read_bytes() == b'recording'
    duplicate = recording(root, 'renamed.mp4')
    before = (root / '.processed.json').read_bytes()
    result = execute(root, notes, duplicate, lambda *a: pytest.fail('duplicate must not reprocess'))
    assert result['status'] == 'skipped' and not duplicate.exists()
    assert (root / 'processed/renamed.mp4').read_bytes() == b'recording'
    assert (root / '.processed.json').read_bytes() == before


@pytest.mark.parametrize('artifact', ['note', 'evidence', 'processed'])
def test_changed_completed_artifact_stops_duplicate(roots, artifact):
    root, notes = roots
    result = execute(root, notes, recording(root))
    receipt = next((root / '.inbox/receipts').glob('*.json'))
    record = json.loads(receipt.read_text())
    path = Path(result[artifact]) if artifact != 'evidence' else Path(record['evidence'][0]['path'])
    path.write_bytes(b'changed')
    duplicate = recording(root, 'renamed.mp4')
    with pytest.raises(ValueError):
        execute(root, notes, duplicate, lambda *a: pytest.fail('must refuse changed artifacts'))
    assert duplicate.exists() and path.read_bytes() == b'changed'


def test_changed_source_never_publishes_or_moves(roots):
    root, notes = roots
    source = recording(root)
    def changed(*args):
        value = producer(*args)
        source.write_bytes(b'changed during read')
        return value
    with pytest.raises(ValueError, match='recording changed'):
        execute(root, notes, source, changed)
    assert source.exists() and not notes.exists()


def test_move_collision_preserves_both_sources(roots):
    root, notes = roots
    source = recording(root)
    destination = recording(root, 'processed/recording.mp4', b'other recording')
    with pytest.raises(ValueError, match='collision'):
        execute(root, notes, source)
    assert source.read_bytes() == b'recording'
    assert destination.read_bytes() == b'other recording'


def test_crash_after_receipt_before_note_recovers_original_draft(roots, monkeypatch):
    root, notes = roots
    source = recording(root)
    original = inbox.exclusive
    def interrupted(path, data):
        if path.suffix == '.md' and notes in path.parents:
            raise OSError('simulated publication interruption')
        return original(path, data)
    monkeypatch.setattr(inbox, 'exclusive', interrupted)
    with pytest.raises(OSError):
        execute(root, notes, source)
    assert source.exists() and list((root / '.inbox/receipts').glob('*.json'))
    monkeypatch.setattr(inbox, 'exclusive', original)
    result = execute(root, notes, source, lambda *a: pytest.fail('resume must reuse original draft'))
    assert result['status'] == 'processed'


def test_crash_after_move_recovers_checkpoint(roots, monkeypatch):
    root, notes = roots
    source = recording(root)
    original = inbox.mark
    def interrupted(root, identity, receipt, status):
        if status == 'processed':
            raise OSError('crash after source unlink')
        return original(root, identity, receipt, status)
    monkeypatch.setattr(inbox, 'mark', interrupted)
    with pytest.raises(OSError):
        execute(root, notes, source)
    assert not source.exists()
    monkeypatch.setattr(inbox, 'mark', original)
    inbox.recover(root, notes)
    assert all(item['status'] == 'processed' for item in inbox.checkpoint(root)['items'].values())


def test_failed_link_unlink_window_resumes(roots, monkeypatch):
    root, notes = roots
    source = recording(root)
    original = Path.unlink
    def interrupted(path, *args, **kwargs):
        if path == source:
            raise OSError('source unlink failed')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'unlink', interrupted)
    with pytest.raises(OSError):
        execute(root, notes, source)
    assert source.exists() and (root / 'processed/recording.mp4').exists()
    monkeypatch.setattr(Path, 'unlink', original)
    assert execute(root, notes, source, lambda *a: pytest.fail('do not regenerate'))['status'] == 'processed'


@pytest.mark.parametrize('gate', ['requires_cloud_approval', 'needs_model_download', 'needs_install'])
def test_unsafe_or_missing_gate_never_reads(roots, tmp_path, monkeypatch, gate):
    root, _ = roots
    source = recording(root)
    calls = []
    def invoke(command, *args):
        calls.append(command)
        if command == 'inspect':
            return {'source': 'local', 'sidecar_transcript': 'test.srt'}
        if command == 'preview':
            result = {'backend': 'captions', 'free': True, 'requires_cloud_approval': False,
                      'needs_model_download': False, 'needs_install': False}
            del result[gate]
            return result
        pytest.fail('unsafe gate must not reach read')
    monkeypatch.setattr(inbox, 'invoke_reader', invoke)
    with pytest.raises(ValueError, match='safe gates'):
        inbox.prepare(source, tmp_path, 'cached', 'auto', 11434)
    assert calls == ['inspect', 'preview']


def test_unrecognized_checkpoint_preserved(roots):
    root, notes = roots
    path = root / '.processed.json'
    path.write_text('{"other-tool":true}')
    with pytest.raises(ValueError, match='unrecognized'):
        execute(root, notes, recording(root))
    assert path.read_text() == '{"other-tool":true}'


def test_interrupted_authoring_reuses_completed_reader_bundle(roots, monkeypatch):
    root, notes = roots
    source = recording(root)
    calls = []
    def invoke(command, source, work, *options):
        calls.append(command)
        if command == 'inspect':
            return {'source': 'local', 'duration_s': 4}
        if command == 'preview':
            return {'backend': 'captions', 'free': True, 'requires_cloud_approval': False,
                    'needs_model_download': False, 'needs_install': False}
        bundle = work / 'evidence'
        bundle.mkdir()
        transcript = bundle / 'transcript.txt'
        transcript.write_text('[00:00] Retained transcript.\n')
        result = {'status': 'complete', 'backend': 'captions', 'transcript': str(transcript)}
        (bundle / 'manifest.json').write_text(json.dumps(result))
        return result
    monkeypatch.setattr(inbox, 'invoke_reader', invoke)
    monkeypatch.setattr(inbox.local_notes, 'draft', lambda *a, **kw: (_ for _ in ()).throw(ValueError('model interrupted')))
    with pytest.raises(ValueError, match='model interrupted'):
        inbox.process_one(root, notes, source, 'cached', 'captions', 11434)
    assert source.exists() and calls == ['inspect', 'preview', 'read']
    calls.clear()
    def local_draft(bundle, draft, model, **kwargs):
        draft.write_text('# Review\n\nSource: synthetic transcript\n\n## Synopsis\nRetained transcript.\n\n## Action Items\nNone.\n'
                         '\n## Key moments\n[00:00] Retained transcript.\n\n## Full Transcript\n'
                         '    [00:00] Retained transcript.\n')
    monkeypatch.setattr(inbox.local_notes, 'draft', local_draft)
    result = inbox.process_one(root, notes, source, 'cached', 'captions', 11434)
    assert result['status'] == 'processed'
    assert calls == ['inspect', 'preview'], 'completed reader must not run again'
    note = Path(result['note']).read_text()
    assert note.startswith('# Review\n') and 'Duration seconds: 4' in note and 'Language: unknown' in note
    assert 'Source: synthetic transcript' not in note


def test_missing_previously_published_note_is_not_silently_restored(roots):
    root, notes = roots
    result = execute(root, notes, recording(root))
    Path(result['note']).unlink()
    source = recording(root, 'duplicate.mp4')
    with pytest.raises(ValueError, match='regular file'):
        execute(root, notes, source)
    assert source.exists() and not Path(result['note']).exists()


def test_failed_file_does_not_block_next_selected_file(roots, monkeypatch):
    root, notes = roots
    bad, good = recording(root, 'bad.mp4', b'bad'), recording(root, 'good.mp4', b'good')
    os.utime(bad, (1, 1))
    def runner(command, **kwargs):
        source = Path(command[command.index('--source') + 1])
        if source == bad:
            raise inbox.ProcessDeadlineError('synthetic deadline')
        result = execute(root, notes, source)
        Path(command[command.index('--result') + 1]).write_text(json.dumps(result))
    monkeypatch.setattr(inbox, 'bounded_worker', runner)
    result = inbox.process(root, notes, 'cached', apply=True)
    assert result['failed'] == 1 and result['processed'] == 1
    assert bad.exists() and not good.exists()


def test_receipt_change_cannot_redirect_source_movement(roots):
    root, notes = roots
    result = execute(root, notes, recording(root))
    receipt = next((root / '.inbox/receipts').glob('*.json'))
    record = json.loads(receipt.read_text())
    record['original_name'] = '../outside.mp4'
    receipt.write_text(json.dumps(record))
    source = recording(root, 'duplicate.mp4')
    with pytest.raises(ValueError, match='receipt changed'):
        execute(root, notes, source)
    assert source.exists()


def test_evidence_sync_failure_prevents_publication_and_move(roots, monkeypatch):
    root, notes = roots
    source = recording(root)
    def failed_sync(path):
        raise OSError('cannot retain evidence durably')
    monkeypatch.setattr(inbox, 'retain', failed_sync)
    with pytest.raises(OSError):
        execute(root, notes, source)
    assert source.exists() and not notes.exists()


def test_oversized_checkpoint_is_rejected_before_index_writes(roots):
    root, _ = roots
    path = root / '.processed.json'
    with path.open('wb') as stream:
        stream.truncate(4 * 1024 * 1024 + 1)
    with pytest.raises(ValueError, match='metadata exceeds'):
        inbox.mark(root, 'a' * 64, root / 'unread-receipt.json', 'processed')
    assert not list(root.glob('.inbox-index-*'))


def test_discovery_bounds_empty_directories_too(roots, monkeypatch):
    root, _ = roots
    monkeypatch.setattr(inbox.os, 'walk', lambda *a, **kw: iter([(str(root), ['unused'] * 10001, [])]))
    with pytest.raises(ValueError, match='10000 entries'):
        inbox.discover(root, 10)


def test_named_event_routes_note_and_retains_processed_subfolders(roots):
    root, notes = roots
    source = recording(root, 'Conference 2026/Day 2/talk.mp4')
    result = execute(root, notes, source)
    assert Path(result['note']).parent == notes / 'Conference/Conference 2026'
    assert Path(result['processed']) == root / 'processed/Conference 2026/Day 2/talk.mp4'
    duplicate = recording(root, 'Another Event/renamed.mp4')
    result = execute(root, notes, duplicate, lambda *a: pytest.fail('same recording must not be reanalyzed'))
    assert result['status'] == 'skipped' and not duplicate.exists()
    assert (root / 'processed/Another Event/renamed.mp4').read_bytes() == b'recording'


def test_duplicate_does_not_starve_next_bounded_batch(roots):
    root, notes = roots
    execute(root, notes, recording(root))
    duplicate = recording(root, 'duplicate.mp4')
    os.utime(duplicate, (1, 1))
    fresh = recording(root, 'new.mp4', b'new recording')
    assert inbox.discover(root, 1) == [duplicate]
    assert execute(root, notes, duplicate)['status'] == 'skipped'
    assert inbox.discover(root, 1) == [fresh]


def test_duplicate_destination_collision_preserves_input(roots):
    root, notes = roots
    execute(root, notes, recording(root))
    duplicate = recording(root, 'renamed.mp4')
    destination = recording(root, 'processed/renamed.mp4', b'other recording')
    with pytest.raises(ValueError, match='collision'):
        execute(root, notes, duplicate)
    assert duplicate.read_bytes() == b'recording'
    assert destination.read_bytes() == b'other recording'
