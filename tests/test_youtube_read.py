import json
import io
from pathlib import Path
import subprocess

import pytest

import youtube_ingest_helper as ingest
import youtube_read as reader
from test_youtube_ingest import snapshot, URL


def fixture(tmp_path, *, gates=None, complete=True, visual=False):
    root = tmp_path / 'capture'
    ingest.process_snapshot(root, snapshot(), apply=True)
    work = tmp_path / 'work'
    work.mkdir()
    calls = []
    def invoke(command, url, out, *options):
        calls.append(command)
        assert url == URL
        displayed, redacted = reader.redact_remote_url(url)
        if command == 'inspect':
            return {'source': 'url', 'input': displayed, 'input_redacted': redacted,
                    'youtube_id': 'abcdefghijk', 'captions_available': True}
        if command == 'preview':
            return {'input': displayed, 'input_redacted': redacted, 'backend': 'none' if visual else 'captions', 'free': True,
                    'requires_cloud_approval': False, 'needs_model_download': False,
                    'needs_install': False, **(gates or {})}
        bundle = Path(options[options.index('--workdir') + 1])
        bundle.mkdir()
        transcript = bundle / 'transcript.txt'
        transcript.write_text('[00:00] An example sentence.\n[00:04] A second point.\n')
        frame = bundle / 'frame.jpg'
        frame.write_bytes(b'synthetic')
        data = {'status': 'complete' if complete else 'partial', 'backend': 'none' if visual else 'captions',
                'workdir': str(bundle), 'frames': [{'file': str(frame), 't': '00:02'}],
                'transcript': None if visual else str(transcript)}
        (bundle / 'manifest.json').write_text(json.dumps(data))
        return data
    return root, work, calls, invoke


def test_read_stages_and_verified_reuse(tmp_path):
    root, work, calls, invoke = fixture(tmp_path)
    result = reader.prepare(root, 'youtube:abcdefghijk', work, reader=invoke)
    assert result['status'] == 'ready' and calls == ['inspect', 'preview', 'read']
    result = reader.prepare(root, 'youtube:abcdefghijk', work, reader=lambda *a: pytest.fail('read again'))
    assert result['duplicate']
    with pytest.raises(ValueError, match='different settings'):
        reader.prepare(root, 'youtube:abcdefghijk', work, backend='faster-whisper', reader=invoke)


@pytest.mark.parametrize('gates', [{'requires_cloud_approval': True}, {'needs_model_download': True},
                                 {'needs_install': True}, {'free': False}, {'needs_install': None},
                                 {'backend': 'groq'}, {'input': 'https://other.example/'}])
def test_preview_gate_prevents_read(tmp_path, gates):
    root, work, calls, invoke = fixture(tmp_path, gates=gates)
    with pytest.raises(ValueError):
        reader.prepare(root, 'youtube:abcdefghijk', work, reader=invoke)
    assert calls == ['inspect', 'preview'] and not (work / 'ready.json').exists()


def test_partial_read_cannot_be_ready(tmp_path):
    root, work, calls, invoke = fixture(tmp_path, complete=False)
    with pytest.raises(ValueError):
        reader.prepare(root, 'youtube:abcdefghijk', work, reader=invoke)
    assert not (work / 'ready.json').exists()


def test_changed_evidence_cannot_resume(tmp_path):
    root, work, calls, invoke = fixture(tmp_path)
    reader.prepare(root, 'youtube:abcdefghijk', work, reader=invoke)
    (work / 'evidence/transcript.txt').write_text('changed')
    with pytest.raises(ValueError, match='changed'):
        reader.prepare(root, 'youtube:abcdefghijk', work, reader=invoke)


def test_visual_evidence_does_not_require_transcription(tmp_path):
    root, work, calls, invoke = fixture(tmp_path, visual=True)
    reader.prepare(root, 'youtube:abcdefghijk', work, tier='visual', reader=invoke)
    ready, manifest, artifacts = reader.verify_read(work, 'youtube:abcdefghijk')
    assert ready['backend'] == 'none' and manifest['transcript'] is None


def test_read_authority_precedes_io(tmp_path):
    with pytest.raises(PermissionError):
        reader.read(tmp_path / 'absent', 'youtube:abcdefghijk', tmp_path / 'work')
    assert list(tmp_path.iterdir()) == []


def test_wrong_source_probe_prevents_preview(tmp_path):
    root, work, calls, invoke = fixture(tmp_path)
    with pytest.raises(ValueError, match='different source'):
        reader.prepare(root, 'youtube:abcdefghijk', work, reader=lambda *a: {'source': 'local', 'input': 'wrong'})


def test_invocation_clears_legacy_cookie_binding(tmp_path, monkeypatch):
    monkeypatch.setenv('READ_VIDEO_YTDLP_COOKIES', 'synthetic-do-not-read')
    def run(args, **options):
        assert options['env']['READ_VIDEO_YTDLP_COOKIES'] == ''
        options['stdout'].write(b'{"source":"url"}')
        return subprocess.CompletedProcess(args, 0)
    monkeypatch.setattr(reader.subprocess, 'run', run)
    assert reader.invoke('inspect', URL, tmp_path)['source'] == 'url'


@pytest.mark.parametrize('payload', [b'{"ok":true}', b'{"error":{}}', b'[]'])
def test_invocation_rejects_wrong_envelope(tmp_path, monkeypatch, payload):
    def run(args, **options):
        options['stdout'].write(payload)
        return subprocess.CompletedProcess(args, 0)
    monkeypatch.setattr(reader.subprocess, 'run', run)
    with pytest.raises(ValueError):
        reader.invoke('inspect', URL, tmp_path)


def test_failed_invocation_does_not_parse_success(tmp_path, monkeypatch):
    monkeypatch.setattr(reader.subprocess, 'run', lambda *a, **k: subprocess.CompletedProcess(a, 1))
    with pytest.raises(ValueError, match='reader failed'):
        reader.invoke('inspect', URL, tmp_path)


def test_parent_owns_worker_and_revalidates_result(tmp_path, monkeypatch):
    root, work, calls, invoke = fixture(tmp_path)
    reader.prepare(root, 'youtube:abcdefghijk', work, reader=invoke)
    workers = []
    monkeypatch.setattr(reader, 'run_worker', lambda args, **kwargs: workers.append((args, kwargs)))
    result = reader.read(root, 'youtube:abcdefghijk', work, allow_read=True)
    assert result['status'] == 'ready' and len(workers) == 1
    assert '--worker' in workers[0][0] and workers[0][1]['timeout'] == 1800
    for options in ({'timeout': 0}, {'timeout': 7201}, {'backend': 'groq'}, {'tier': 'other'}):
        with pytest.raises(ValueError):
            reader.read(root, 'youtube:abcdefghijk', work, allow_read=True, **options)


def test_cli_worker_handshake_and_public_dispatch(tmp_path, monkeypatch, capsys):
    base = ['capture', 'youtube:abcdefghijk', str(tmp_path / 'work')]
    monkeypatch.setattr(reader.sys, 'stdin', io.StringIO('NO\n'))
    assert reader.main([*base, '--worker']) == 6
    assert not json.loads(capsys.readouterr().out)['ok']
    monkeypatch.setattr(reader.sys, 'stdin', io.StringIO('GO\n'))
    monkeypatch.setattr(reader, 'prepare', lambda **kwargs: {'status': 'ready'})
    assert reader.main([*base, '--worker']) == 0
    assert json.loads(capsys.readouterr().out)['data']['status'] == 'ready'
    monkeypatch.setattr(reader, 'read', lambda **kwargs: {'status': 'ready'})
    assert reader.main([*base, '--allow-read']) == 0
    capsys.readouterr()


@pytest.mark.parametrize('change', ['key', 'empty', 'too_many', 'missing_manifest', 'manifest_status',
                                  'missing_frame', 'missing_transcript', 'no_media'])
def test_read_receipt_and_manifest_structure(tmp_path, change):
    root, work, calls, invoke = fixture(tmp_path)
    reader.prepare(root, 'youtube:abcdefghijk', work, reader=invoke)
    path = work / 'ready.json'
    ready = json.loads(path.read_text())
    manifest_path = work / 'evidence/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if change == 'key':
        ready['key'] = 'youtube:lmnopqrstuv'
    elif change == 'empty':
        ready['artifacts'] = []
    elif change == 'too_many':
        ready['artifacts'] *= 200
    elif change == 'missing_manifest':
        ready['artifacts'] = [a for a in ready['artifacts'] if a['path'] != 'manifest.json']
    else:
        if change == 'manifest_status':
            manifest['status'] = 'partial'
        elif change == 'missing_frame':
            manifest['frames'][0]['file'] = str(work / 'evidence/absent.jpg')
        elif change == 'missing_transcript':
            manifest['transcript'] = str(work / 'evidence/absent.txt')
        else:
            manifest['frames'] = []
            manifest['transcript'] = None
        manifest_path.write_text(json.dumps(manifest))
        for artifact in ready['artifacts']:
            if artifact['path'] == 'manifest.json':
                artifact['sha256'] = reader.file_digest(manifest_path)
    path.write_text(json.dumps(ready))
    with pytest.raises((ValueError, KeyError, TypeError)):
        reader.verify_read(work, 'youtube:abcdefghijk')


def test_prepare_limits_before_ready_publication(tmp_path):
    root, work, calls, invoke = fixture(tmp_path)
    with pytest.raises(ValueError):
        reader.prepare(root, 'youtube:abcdefghijk', work, backend='groq', reader=invoke)
    def large_info(command, *args):
        data = invoke(command, *args)
        if command == 'inspect':
            data['title'] = 'x' * (1024 * 1024)
        return data
    with pytest.raises(ValueError, match='receipt exceeds'):
        reader.prepare(root, 'youtube:abcdefghijk', work, reader=large_info)
    assert not (work / 'ready.json').exists()


def test_prepare_artifact_count_cap(tmp_path):
    root, work, calls, invoke = fixture(tmp_path)
    def many_files(command, *args):
        data = invoke(command, *args)
        if command == 'read':
            for number in range(513):
                (work / 'evidence' / f'file{number}').write_text('x')
        return data
    with pytest.raises(ValueError, match='too many artifacts'):
        reader.prepare(root, 'youtube:abcdefghijk', work, reader=many_files)
    assert not (work / 'ready.json').exists()
