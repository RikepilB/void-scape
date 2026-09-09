"""Whisper controls preserve actual timing evidence and explicit backend intent."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import video
import voidscape


class Model:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def transcribe(self, audio, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise TypeError('unsupported options: SYNTHETIC_VOCABULARY')
        return [SimpleNamespace(start=0.5, text='Hello world', words=[
            SimpleNamespace(start=1.23456, end=1.7, word='Hello', probability=0.9),
            SimpleNamespace(start=2.25, end=2.6, word=' world', probability=0.8)])], None


def setup_model(monkeypatch, model):
    monkeypatch.setattr(video, '_whisper_settings', lambda: ('small', None))
    def load(size, root, offline):
        assert offline is True
        return model
    monkeypatch.setattr(video, '_new_whisper', load)


def probe(inp):
    return {'input': inp, 'source': 'local', 'duration_s': 100.0, 'width': 640,
            'height': 360, 'captions_available': True, 'sidecar_transcript': 'unused.srt'}


def test_controls_reach_cached_model_and_use_first_word_timing(monkeypatch):
    model = Model()
    setup_model(monkeypatch, model)
    text = video._faster_whisper('unused.wav', word_timestamps=True,
                                 initial_prompt='SYNTHETIC_VOCABULARY', source_offset_s=0.00049)
    assert text == '[00:01.235] Hello world'
    assert model.calls == [{'vad_filter': True, 'word_timestamps': True,
                           'initial_prompt': 'SYNTHETIC_VOCABULARY'}]


@pytest.mark.parametrize('options', [{'word_timestamps': True}, {'initial_prompt': 'SYNTHETIC_VOCABULARY'}])
def test_requested_options_are_not_silently_dropped(monkeypatch, options):
    model = Model(fail=True)
    setup_model(monkeypatch, model)
    with pytest.raises(RuntimeError, match='no option-free retry') as error:
        video._faster_whisper('unused.wav', **options)
    assert len(model.calls) == 1
    assert 'SYNTHETIC_VOCABULARY' not in str(error.value)


@pytest.mark.parametrize('start,end', [(float('nan'), 1), (-1, 1), (2, 1), (1, float('inf'))])
def test_invalid_word_times_fail(start, end):
    segment = SimpleNamespace(text='word', words=[SimpleNamespace(start=start, end=end, word='word')])
    with pytest.raises(RuntimeError, match='invalid word timestamps'):
        video._render_whisper([segment], True, 'synthetic')


def test_missing_word_data_does_not_get_fake_precision():
    with pytest.raises(RuntimeError, match='without requested word timestamps'):
        video._render_whisper([SimpleNamespace(start=1, text='speech', words=None)], True, 'synthetic')


def test_silence_is_empty_evidence_not_a_timing_failure():
    assert video._render_whisper([SimpleNamespace(text='', words=None)], True, 'synthetic') == ''


@pytest.mark.parametrize('backend', ['captions', 'groq', 'faster-whisper,groq'])
def test_incompatible_backend_rejected_in_preview_and_read(monkeypatch, tmp_path, backend):
    monkeypatch.setattr(video, 'probe', probe)
    for operation in (video.estimate, video.run):
        with pytest.raises(ValueError, match='only local/faster-whisper'):
            operation('unused.mp4', backend=backend, word_timestamps=True)
    assert not list(tmp_path.iterdir())


def test_sidecar_does_not_hide_model_download_gate(monkeypatch, tmp_path):
    monkeypatch.setattr(video, 'probe', probe)
    monkeypatch.setattr(video, '_have_local_backend', lambda *args: True)
    monkeypatch.setattr(video, '_model_download_info', lambda want, *args: {
        'status': 'required' if want else 'not_needed', 'model': 'synthetic'})
    estimate = video.estimate('unused.mp4', backend='faster-whisper', word_timestamps=True)
    assert estimate['sidecar_transcript'] is None
    assert estimate['gate']['type'] == 'model_download'
    with pytest.raises(video.ApprovalRequired):
        video.run('unused.mp4', backend='faster-whisper', word_timestamps=True,
                  workdir=str(tmp_path / 'output'))
    assert not (tmp_path / 'output').exists()


@pytest.mark.parametrize('guided', [False, True])
def test_scoped_read_records_word_evidence_and_retains_alignment(tmp_path, monkeypatch, capsys, guided):
    model = Model()
    setup_model(monkeypatch, model)
    monkeypatch.setattr(video, 'probe', probe)
    monkeypatch.setattr(video, '_have', lambda *args: True)
    monkeypatch.setattr(video, '_have_local_backend', lambda *args: True)
    monkeypatch.setattr(video, '_model_download_info', lambda *args: {'status': 'cached', 'model': 'small'})
    monkeypatch.setattr(video, '_to_audio', lambda *args, **kwargs: 'synthetic-scoped.wav')
    monkeypatch.setattr(voidscape, '_load_workspace', lambda *args: {})
    ref = tmp_path / 'ref.txt'
    ref.write_text('Hello, world!')
    root = tmp_path / 'output'
    args = ['unused.mp4', '--tier', 'audio', '--backend', 'faster-whisper', '--transcribe-mode', 'fast',
            '--word-timestamps', '--initial-prompt', 'SYNTHETIC_VOCABULARY',
            '--align-reference', str(ref), '--start', '65.01', '--end', '75', '--workdir', str(root)]
    code = (voidscape.main(['read', *args, '--json']) if guided else video.main(['run', *args, '--envelope']))
    captured = capsys.readouterr()
    assert code == 0
    assert 'SYNTHETIC_VOCABULARY' not in captured.out + captured.err
    output = json.loads(captured.out)
    result = output if guided else output['data']
    assert result['whisper_options'] == {'word_timestamps': True, 'initial_prompt_supplied': True, 'model': 'small'}
    assert Path(result['transcript']).read_text() == '[01:06.245] Hello, world!'
    words = json.loads(Path(result['words_file']).read_text())
    assert words['words'][0]['start_s'] == pytest.approx(66.24456)
    assert words['words'][0]['end_s'] == pytest.approx(66.71)
    assert words['words'][0]['model_start_s'] == 1.23456
    assert words['words'][0]['source_offset_s'] == 65.01
    assert words['words'][0]['word'] == 'Hello'
    assert words['applies_to'] == 'baseline_transcript_before_reference_alignment'
    assert 'words.json' in json.loads((root / '.agent/latest-read.json').read_text())['evidence']
    assert 'SYNTHETIC_VOCABULARY' not in (root / 'manifest.json').read_text()
    assert 'word_timing' in result['stages_completed']


def test_stop_does_not_apply_controls_or_require_a_model(tmp_path, monkeypatch):
    monkeypatch.setattr(video, 'probe', probe)
    def forbidden(*args):
        pytest.fail('model invoked for stopped read')
    monkeypatch.setattr(video, '_new_whisper', forbidden)
    estimate = video.estimate('unused.mp4', stop_at='probe', word_timestamps=True, initial_prompt='vocab')
    result = video.run('unused.mp4', stop_at='probe', word_timestamps=True,
                       initial_prompt='vocab', workdir=str(tmp_path))
    assert 'whisper_options' not in estimate
    assert 'whisper_options' not in result
    assert 'words_file' not in result
    assert result['status'] == 'stopped'


def test_millisecond_label_shift_and_carry():
    assert video._shift_transcript_timestamps('[00:59.999] word', 0.002) == '[01:00.001] word'
    assert video._shift_transcript_timestamps('[00:02] word', 65) == '[01:07] word'


def test_prompt_only_does_not_save_prompt_text(tmp_path, monkeypatch):
    model = Model()
    setup_model(monkeypatch, model)
    monkeypatch.setattr(video, 'probe', probe)
    monkeypatch.setattr(video, '_have', lambda *args: True)
    monkeypatch.setattr(video, '_model_download_info', lambda *args: {'status': 'cached', 'model': 'small'})
    result = video.run('unused.mp4', tier='audio', backend='local', transcribe_mode='fast',
                       initial_prompt='SYNTHETIC_VOCABULARY', workdir=str(tmp_path))
    assert 'words_file' not in result
    assert result['whisper_options']['initial_prompt_supplied'] is True
    assert 'SYNTHETIC_VOCABULARY' not in json.dumps(result)
    assert model.calls[0]['initial_prompt'] == 'SYNTHETIC_VOCABULARY'


def test_control_runtime_errors_do_not_echo_vocabulary(monkeypatch):
    class Failure:
        def transcribe(self, *args, **kwargs):
            raise RuntimeError('SYNTHETIC_VOCABULARY failed in provider')
    setup_model(monkeypatch, Failure())
    with pytest.raises(RuntimeError) as error:
        video._faster_whisper('unused.wav', initial_prompt='SYNTHETIC_VOCABULARY')
    assert 'SYNTHETIC_VOCABULARY' not in str(error.value)


def test_uncached_word_mode_never_downloads_without_consent(monkeypatch):
    monkeypatch.setattr(video, '_whisper_settings', lambda: ('small', None))
    calls = []
    def missing(size, root, offline):
        calls.append(offline)
        assert offline is True
        raise RuntimeError('synthetic cache miss')
    monkeypatch.setattr(video, '_new_whisper', missing)
    with pytest.raises(video.BackendGateError) as error:
        video._faster_whisper('unused.wav', word_timestamps=True)
    assert error.value.gate['type'] == 'model_download'
    assert calls and all(calls)


@pytest.mark.parametrize('command', ['preview', 'read'])
def test_other_reader_rejects_whisper_controls(command, monkeypatch, capsys):
    monkeypatch.setattr(voidscape, '_load_workspace', lambda *args: {})
    assert voidscape.main([command, 'unused', '--reader', 'image', '--word-timestamps', '--json']) == 3
    assert 'Whisper controls' in capsys.readouterr().out


def test_visual_tier_rejects_active_controls(monkeypatch):
    monkeypatch.setattr(video, 'probe', probe)
    for operation in (video.estimate, video.run):
        with pytest.raises(ValueError, match='audio or both'):
            operation('unused.mp4', tier='visual', backend='local', word_timestamps=True)
