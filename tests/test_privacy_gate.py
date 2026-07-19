from pathlib import Path

import pytest

import video


def _probe(inp):
    return {
        "source": "local", "input": inp, "sidecar_transcript": None,
        "captions_available": False, "duration_s": 10.0, "width": 640,
        "height": 360, "fps": 30.0, "has_audio": True,
    }


@pytest.mark.parametrize("backend", [
    "groq", "openai", "openai-mini", "openrouter", "gemini",
    "captions,groq", "faster-whisper,openai",
])
def test_cloud_chain_rejected_before_download_or_audio_conversion(tmp_path, monkeypatch, backend):
    calls = []
    monkeypatch.setattr(video, "probe", _probe)
    monkeypatch.setattr(video, "_download", lambda *args: calls.append("download"))
    monkeypatch.setattr(video, "_to_audio", lambda *args: calls.append("audio"))
    monkeypatch.setattr(video, "_api_transcribe", lambda *args: calls.append("upload"))
    monkeypatch.setattr(video, "_gemini", lambda *args: calls.append("upload"))

    with pytest.raises(PermissionError, match="allow-cloud"):
        video.run("x.mp4", tier="audio", backend=backend, workdir=str(tmp_path))

    assert calls == []
    assert not (Path(tmp_path) / "audio.mp3").exists()


def test_cloud_chain_runs_only_after_explicit_approval(tmp_path, monkeypatch):
    monkeypatch.setattr(video, "probe", _probe)
    monkeypatch.setattr(video, "_transcribe", lambda *args, **kwargs: ("transcript.txt", "ok"))

    out = video.run("x.mp4", tier="audio", backend="groq", workdir=str(tmp_path),
                    allow_cloud=True)

    assert out["transcript_chars"] == 2


def test_cloud_chain_not_gated_when_sidecar_resolves_for_free(tmp_path, monkeypatch):
    """A sidecar transcript short-circuits _transcribe() before the chain is ever consulted, so
    naming a cloud backend as a fallback preference must not demand --allow-cloud."""
    sidecar = tmp_path / "clip.srt"
    sidecar.write_text("1\n00:00:00,000 --> 00:00:01,000\nhello\n", encoding="utf-8")

    calls = []
    monkeypatch.setattr(video, "probe",
                        lambda inp: {**_probe(inp), "sidecar_transcript": str(sidecar)})
    monkeypatch.setattr(video, "_download", lambda *args: calls.append("download"))
    monkeypatch.setattr(video, "_to_audio", lambda *args: calls.append("audio"))
    monkeypatch.setattr(video, "_api_transcribe", lambda *args: calls.append("upload"))

    out = video.run("x.mp4", tier="audio", backend="groq", workdir=str(tmp_path))

    assert calls == []
    assert out["transcript_chars"] > 0
