from types import SimpleNamespace

import pytest

import video


class FakeModel:
    def __init__(self, fail_on_kwargs=False):
        self.calls = []
        self.fail_on_kwargs = fail_on_kwargs

    def transcribe(self, audio, **kwargs):
        self.calls.append((audio, kwargs))
        if self.fail_on_kwargs and kwargs:
            raise TypeError("unsupported kwargs")
        return [SimpleNamespace(start=1.0, text=" hello ")], None


def test_model_available_locally_reuses_new_whisper_offline_probe(monkeypatch):
    """Must not hardcode an HF repo-id guess -- large/distil/turbo variants use different orgs
    than the plain 'Systran/faster-whisper-<size>' pattern. Reusing _new_whisper's real
    WhisperModel resolution keeps estimate()'s cache check honest for every model name."""
    calls = []

    def fake_new_whisper(size, root, offline):
        calls.append((size, root, offline))
        if size == "large":
            raise RuntimeError("not cached")
        return object()

    monkeypatch.setattr(video, "_new_whisper", fake_new_whisper)

    assert video._model_available_locally("small", "root") is True
    assert video._model_available_locally("large", "root") is False
    assert calls == [("small", "root", True), ("large", "root", True)]


def test_transcribe_profile_routes_by_threshold(monkeypatch):
    monkeypatch.setattr(video, "load_workspace", lambda: {})
    assert video._transcribe_profile(45.0, threshold_s=45.0) == "fast"
    assert video._transcribe_profile(45.1, threshold_s=45.0) == "thorough"
    assert video._transcribe_profile(None, threshold_s=45.0) == "fast"


def test_transcribe_profile_override_wins():
    assert video._transcribe_profile(999.0, override="fast") == "fast"
    assert video._transcribe_profile(1.0, override="thorough") == "thorough"
    with pytest.raises(ValueError, match="transcribe-mode"):
        video._transcribe_profile(1.0, override="deep")


def test_transcribe_threshold_reads_workspace_and_env(monkeypatch):
    monkeypatch.delenv("READ_VIDEO_TRANSCRIPTION_THOROUGH_THRESHOLD_S", raising=False)
    monkeypatch.setattr(video, "load_workspace", lambda: {"transcription_thorough_threshold_s": 30})
    assert video._transcribe_threshold() == 30.0
    monkeypatch.setenv("READ_VIDEO_TRANSCRIPTION_THOROUGH_THRESHOLD_S", "75")
    assert video._transcribe_threshold() == 75.0


def test_faster_whisper_fast_profile_keeps_existing_kwargs(monkeypatch):
    model = FakeModel()
    sizes = []
    monkeypatch.setattr(video, "_whisper_settings", lambda: ("small", None))
    monkeypatch.setattr(video, "_new_whisper", lambda size, root, offline: sizes.append(size) or model)

    assert video._faster_whisper("audio.mp3", duration_s=45.0) == "[00:01] hello"
    assert sizes == ["small"]
    assert model.calls == [("audio.mp3", {"vad_filter": True})]


def test_faster_whisper_thorough_profile_uses_medium_and_tuned_kwargs(monkeypatch):
    model = FakeModel()
    sizes = []
    monkeypatch.setattr(video, "_whisper_settings", lambda: ("small", None))
    monkeypatch.setattr(video, "_new_whisper", lambda size, root, offline: sizes.append(size) or model)

    assert video._faster_whisper("audio.mp3", duration_s=46.0) == "[00:01] hello"
    assert sizes == ["medium"]
    assert model.calls == [("audio.mp3", {
        "vad_filter": True,
        "condition_on_previous_text": False,
        "vad_parameters": {"min_silence_duration_ms": 500, "speech_pad_ms": 300},
    })]


def test_faster_whisper_degrades_when_vad_parameters_unsupported(monkeypatch):
    model = FakeModel(fail_on_kwargs=True)
    monkeypatch.setattr(video, "_whisper_settings", lambda: ("small", None))
    monkeypatch.setattr(video, "_new_whisper", lambda size, root, offline: model)

    assert video._faster_whisper("audio.mp3", duration_s=46.0) == "[00:01] hello"
    assert model.calls[-1] == ("audio.mp3", {})


def test_faster_whisper_degrades_to_cached_fallback_without_download_consent(monkeypatch):
    """Requested ('medium') fails offline, but a cached fallback ('small') succeeds -- must NOT
    raise even with allow_model_download=False, since no actual download is needed."""
    model = FakeModel()
    sizes = []

    def fake_new_whisper(size, root, offline):
        sizes.append(size)
        if size == "medium":
            raise RuntimeError("not cached")
        return model

    monkeypatch.setattr(video, "_whisper_settings", lambda: ("small", None))
    monkeypatch.setattr(video, "_new_whisper", fake_new_whisper)

    result = video._faster_whisper("audio.mp3", duration_s=46.0, allow_model_download=False)

    assert result == "[00:01] hello"
    assert sizes == ["medium", "small"]


def test_estimate_reports_forced_transcribe_mode(monkeypatch):
    monkeypatch.setattr(video, "probe", lambda inp: {
        "source": "local", "input": inp, "sidecar_transcript": None,
        "captions_available": False, "duration_s": 10.0, "width": 640,
        "height": 360, "fps": 30.0, "has_audio": True,
    })
    out = video.estimate("x.mp4", tier="audio", backend="faster-whisper",
                         pr=video.DEFAULT_PRICING, transcribe_mode="thorough")
    assert out["transcribe_mode"] == "thorough"


def test_cli_forwards_transcribe_mode_to_run(monkeypatch, capsys):
    seen = {}

    def fake_run(*args, **kwargs):
        seen["args"] = args
        seen["kwargs"] = kwargs
        return {"ok": True}

    monkeypatch.setattr(video, "run", fake_run)
    assert video.main(["run", "x.mp4", "--transcribe-mode", "thorough",
                       "--allow-model-download", "--allow-cloud"]) == 0
    assert seen["kwargs"]["transcribe_mode"] == "thorough"
    assert seen["kwargs"]["allow_model_download"] is True
    assert seen["kwargs"]["allow_cloud"] is True


def test_thorough_model_download_requires_explicit_approval(monkeypatch):
    monkeypatch.setattr(video, "_whisper_settings", lambda: ("small", None))
    monkeypatch.setattr(video, "_new_whisper", lambda size, root, offline: (_ for _ in ()).throw(
        RuntimeError("not cached")))

    with pytest.raises(RuntimeError, match="allow-model-download"):
        video._faster_whisper("audio.mp3", duration_s=46.0)
