"""Alignment changes text only with explicit provenance and intact baseline timing."""
import hashlib
import json
from pathlib import Path

import pytest
import transcript_alignment as alignment
import video
import voidscape


def reference(tmp_path, text='Hello, world!\nA second sentence.'):
    path = tmp_path / 'reference.txt'
    path.write_text(text, encoding='utf-8')
    return path


def probe(inp):
    return {'source': 'local', 'input': inp, 'duration_s': 10.0, 'width': 640,
            'height': 360, 'sidecar_transcript': None, 'captions_available': False}


def test_high_similarity_replaces_text_and_low_similarity_keeps_baseline(tmp_path):
    ref = alignment.load_reference(reference(tmp_path))
    baseline = '[00:01.250] Hello world\n[00:03] Unrelated speech here'
    result = alignment.align(baseline, ref, baseline_source='whisper')
    assert result['text'] == '[00:01.250] Hello, world!\n[00:03] Unrelated speech here'
    assert [item['timestamp'] for item in result['segments']] == ['00:01.250', '00:03']
    assert result['segments'][0]['source'] == 'aligned'
    assert result['segments'][0]['original_text'] == 'Hello world'
    assert result['segments'][1]['source'] == 'whisper'
    assert result['segments'][1]['reference_indices'] == []
    assert result['mismatch_count'] == 1
    assert result['end_times_available'] is False
    assert all(item['end_s'] is None for item in result['segments'])


def test_reference_grouping_and_forward_recovery(tmp_path):
    ref = alignment.load_reference(reference(tmp_path, 'One sentence. Two sentences.\nLater words.'))
    result = alignment.align('[00:00] One sentence Two sentences\n[00:02] noise\n[00:04] Later words', ref)
    assert result['segments'][0]['reference_indices'] == [0, 1]
    assert result['segments'][2]['reference_indices'] == [2]
    assert result['mismatch_count'] == 1


@pytest.mark.parametrize('text', ['untimed text', '[00:02] later\n[00:01] earlier', '[00:99] invalid', ''])
def test_invalid_baseline_is_rejected(text, tmp_path):
    with pytest.raises(ValueError):
        alignment.align(text, alignment.load_reference(reference(tmp_path)))


@pytest.mark.parametrize('threshold', [-0.01, 1.01, float('nan'), float('inf')])
def test_threshold_bounds(threshold):
    with pytest.raises(ValueError):
        alignment.threshold_value(threshold)


def test_timed_reference_and_exact_snapshot(tmp_path):
    path = tmp_path / 'ref.srt'
    raw = b'1\r\n00:00:01,250 --> 00:00:03,500\r\nHello, world!\r\n\r\n'
    path.write_bytes(raw)
    ref = alignment.load_reference(path)
    assert ref['units'] == [{'text': 'Hello, world!', 'start_s': 1.25, 'end_s': 3.5}]
    wd = tmp_path / 'output'
    wd.mkdir()
    transcript = wd / 'transcript.txt'
    baseline = b'[00:02] Hello world\r\n'
    transcript.write_bytes(baseline)
    result = alignment.write_alignment(wd, transcript, ref, 0.8, 'whisper')
    assert Path(result['original_file']).read_bytes() == baseline
    assert Path(result['reference_file']).read_bytes() == raw
    assert result['reference_sha256'] == hashlib.sha256(raw).hexdigest()
    assert transcript.read_text() == '[00:02] Hello, world!'
    record = json.loads(Path(result['segments_file']).read_text())
    assert record['segments'][0]['start_s'] == 2.0
    assert record['reference_units'][0]['start_s'] == 1.25


@pytest.mark.parametrize('raw', ['bad --> timing\nwords', '1\n00:00:03,000 --> 00:00:01,000\nwords'])
def test_invalid_reference_cues_fail(tmp_path, raw):
    path = tmp_path / 'bad.srt'
    path.write_text(raw)
    with pytest.raises(ValueError):
        alignment.load_reference(path)


def test_reference_size_limit(tmp_path):
    path = tmp_path / 'large.txt'
    path.write_bytes(b'x' * (alignment.MAX_BYTES + 1))
    with pytest.raises(ValueError, match='2 MiB'):
        alignment.load_reference(path)


@pytest.mark.parametrize('backend,gate', [('groq', 'cloud_approval'), ('faster-whisper', 'model_download')])
def test_alignment_suppresses_sidecar_in_both_preview_and_run(tmp_path, monkeypatch, backend, gate):
    ref = reference(tmp_path)
    monkeypatch.setattr(video, 'probe', lambda inp: {**probe(inp), 'sidecar_transcript': str(ref)})
    monkeypatch.setattr(video, '_have_local_backend', lambda *args: True)
    monkeypatch.setattr(video, '_model_download_info', lambda want, *args: {
        'status': 'required' if want and backend == 'faster-whisper' else 'not_needed', 'model': 'synthetic'})
    estimate = video.estimate('clip.mp4', backend=backend, align_reference=str(ref))
    assert estimate['sidecar_transcript'] is None
    assert estimate['gate']['type'] == gate
    with pytest.raises(video.ApprovalRequired) as error:
        video.run('clip.mp4', backend=backend, align_reference=str(ref), workdir=str(tmp_path / 'output'))
    assert error.value.gate['type'] == gate
    assert not (tmp_path / 'output').exists()


@pytest.mark.parametrize('guided', [False, True])
def test_full_read_preserves_provenance_warnings_and_confined_pointer(tmp_path, monkeypatch, capsys, guided):
    ref = reference(tmp_path)
    monkeypatch.setattr(video, 'probe', probe)
    monkeypatch.setattr(voidscape, '_load_workspace', lambda *args: {})
    monkeypatch.setattr(video, '_have_local_backend', lambda *args: True)
    monkeypatch.setattr(video, '_model_download_info', lambda *args: {'status': 'cached', 'model': 'synthetic'})
    def transcribe(orig, info, media, wd, backend, *args):
        assert info['sidecar_transcript'] is None
        return video._save_transcript(wd, '[00:02] Hello world\n[00:04] Entirely unrelated words')
    monkeypatch.setattr(video, '_transcribe_one', transcribe)
    wd = tmp_path / 'output'
    args = ['clip.mp4', '--tier', 'audio', '--backend', 'faster-whisper',
            '--align-reference', str(ref), '--workdir', str(wd)]
    code = (voidscape.main(['read', *args, '--json']) if guided else video.main(['run', *args, '--envelope']))
    output = json.loads(capsys.readouterr().out)
    result = output if guided else output['data']
    assert code == 0
    assert result['status'] == 'complete'
    assert result['alignment']['baseline_source'] == 'whisper'
    assert result['alignment']['baseline_backend'] == 'faster-whisper'
    assert result['alignment']['mismatch_count'] == 1
    assert result['warnings'][0]['code'] == 'alignment_mismatch'
    assert 'align' in result['stages_completed']
    pointer = json.loads((wd / '.agent/latest-read.json').read_text())
    assert set(pointer['evidence']) == {'transcript.txt', 'transcript.original.txt',
                                        'alignment-reference.txt', 'alignment.json'}
    assert all((wd / item).is_file() for item in pointer['evidence'])


def test_alignment_failure_preserves_completed_transcript(tmp_path, monkeypatch, capsys):
    ref = reference(tmp_path)
    monkeypatch.setattr(video, 'probe', probe)
    monkeypatch.setattr(video, '_transcribe_one', lambda orig, info, media, wd, *args:
                        video._save_transcript(wd, 'untimed baseline'))
    wd = tmp_path / 'output'
    code = video.main(['run', 'clip.mp4', '--tier', 'audio', '--backend', 'captions',
                      '--align-reference', str(ref), '--workdir', str(wd), '--envelope'])
    output = json.loads(capsys.readouterr().out)
    assert code != 0
    assert output['ok'] is False
    assert output['meta']['failed_stage'] == 'align'
    assert output['data']['status'] == 'partial'
    assert Path(output['data']['transcript']).read_text() == 'untimed baseline'
    assert not (wd / '.agent/latest-read.json').exists()


def test_stop_does_not_open_alignment_reference(tmp_path, monkeypatch):
    monkeypatch.setattr(video, 'probe', probe)
    def forbidden(*args):
        pytest.fail('reference was opened for a stopped read')
    monkeypatch.setattr(alignment, 'load_reference', forbidden)
    estimate = video.estimate('clip.mp4', stop_at='probe', align_reference='missing.txt')
    result = video.run('clip.mp4', stop_at='probe', align_reference='missing.txt', workdir=str(tmp_path))
    assert 'alignment' not in estimate
    assert 'alignment' not in result
    assert result['status'] == 'stopped'


def test_recovery_rejects_unconfined_alignment_evidence(tmp_path):
    with pytest.raises(ValueError):
        video._evidence_paths({'workdir': str(tmp_path), 'alignment': {
            'original_file': str(tmp_path.parent / 'outside.txt'),
            'reference_file': str(tmp_path / 'ref.txt'), 'segments_file': str(tmp_path / 'align.json')}})


def test_actual_fallback_backend_is_recorded(tmp_path, monkeypatch):
    ref = reference(tmp_path)
    monkeypatch.setattr(video, 'probe', probe)
    monkeypatch.setattr(video, '_model_download_info', lambda *args: {'status': 'cached', 'model': 'synthetic'})
    def transcribe(orig, info, media, wd, backend, *args):
        if backend == 'captions':
            raise RuntimeError('synthetic caption absence')
        return video._save_transcript(wd, '[00:02] Hello world')
    monkeypatch.setattr(video, '_transcribe_one', transcribe)
    result = video.run('clip.mp4', tier='audio', backend='captions,faster-whisper',
                       align_reference=str(ref), workdir=str(tmp_path / 'output'))
    assert result['alignment']['baseline_backend'] == 'faster-whisper'
    assert result['alignment']['baseline_source'] == 'whisper'
    assert result['warnings'][0]['code'] == 'backend_fallback'


def test_same_caption_sidecar_cannot_align_itself(tmp_path, monkeypatch):
    ref = reference(tmp_path)
    monkeypatch.setattr(video, 'probe', lambda inp: {**probe(inp), 'sidecar_transcript': str(ref)})
    for operation in (video.estimate, video.run):
        with pytest.raises(ValueError, match='same sidecar'):
            operation('clip.mp4', backend='captions', align_reference=str(ref))


def test_alignment_preserves_source_time_offset(tmp_path):
    ref = alignment.load_reference(reference(tmp_path))
    baseline = video._shift_transcript_timestamps('[00:02] Hello world', 65)
    result = alignment.align(baseline, ref, baseline_source='whisper')
    assert result['text'] == '[01:07] Hello, world!'
    assert result['segments'][0]['start_s'] == 67
    assert result['segments'][0]['end_s'] is None


def test_failed_provenance_write_does_not_replace_original(tmp_path):
    ref = alignment.load_reference(reference(tmp_path))
    transcript = tmp_path / 'transcript.txt'
    transcript.write_bytes(b'[00:01] Hello world\r\n')
    (tmp_path / 'alignment.json').write_text('existing data')
    with pytest.raises(FileExistsError):
        alignment.write_alignment(tmp_path, transcript, ref, 0.8, 'whisper')
    assert transcript.read_bytes() == b'[00:01] Hello world\r\n'
    assert (tmp_path / 'alignment.json').read_text() == 'existing data'


def test_relative_workdir_recovery_points_to_real_artifacts(tmp_path, monkeypatch):
    ref = reference(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(video, 'probe', probe)
    monkeypatch.setattr(video, '_transcribe_one', lambda orig, info, media, wd, *args:
                        video._save_transcript(wd, '[00:02] Hello world'))
    result = video.run('clip.mp4', tier='audio', backend='captions',
                       align_reference=str(ref), workdir='relative-output')
    root = Path(result['workdir']).resolve()
    pointer = json.loads((root / '.agent/latest-read.json').read_text())
    assert all((root / name).is_file() for name in pointer['evidence'])
    assert 'transcript.txt' in pointer['evidence']
