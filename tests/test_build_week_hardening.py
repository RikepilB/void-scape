from argparse import Namespace
from pathlib import Path

import pytest

import video
import voidscape


def _local_info():
    return {
        "source": "local", "input": "clip.mp4", "sidecar_transcript": None,
        "captions_available": False, "duration_s": 90.0, "width": 640,
        "height": 360, "fps": 30.0, "has_audio": True,
    }


def test_run_extracts_only_approved_audio_window(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(video, "probe", lambda _inp: _local_info())
    monkeypatch.setattr(video, "_have", lambda _module: True)
    monkeypatch.setattr(video, "_model_download_info",
                        lambda *_args: {"status": "cached", "model": "small"})

    def fake_to_audio(src, wd, start=0.0, duration=None):
        calls.append((src, start, duration))
        output = wd / "audio.mp3"
        output.write_bytes(b"scoped")
        return str(output)

    monkeypatch.setattr(video, "_to_audio", fake_to_audio)
    monkeypatch.setattr(video, "_faster_whisper", lambda *_args, **_kwargs: "[00:00] scoped")

    result = video.run("clip.mp4", tier="audio", backend="faster-whisper",
                       start=10.0, end=30.0, workdir=str(tmp_path / "evidence"))

    assert calls == [(str(Path("clip.mp4").resolve()), 10.0, 20.0)]
    assert Path(result["transcript"]).read_text(encoding="utf-8") == "[00:00] scoped"
    assert result["window"] == {"start_s": 10.0, "end_s": 30.0, "duration_s": 20.0}


def test_run_rejects_nonempty_workdir_before_media_work(tmp_path, monkeypatch):
    workdir = tmp_path / "evidence"
    workdir.mkdir()
    (workdir / "old-manifest.json").write_text("stale", encoding="utf-8")
    monkeypatch.setattr(video, "probe", lambda _inp: _local_info())
    touched = []
    monkeypatch.setattr(video, "_download", lambda *_args: touched.append("download"))

    with pytest.raises(ValueError, match="workdir must be empty"):
        video.run("clip.mp4", tier="visual", workdir=str(workdir))

    assert touched == []


def _args(input_value):
    return Namespace(input=input_value, frames=None, backend=None, out_words=600, tier=None,
                     transcribe_mode="auto", agent_model=None)


def test_guided_local_input_defaults_to_local_transcription(monkeypatch):
    seen = {}
    monkeypatch.setattr(voidscape.video, "estimate",
                        lambda _inp, _frames, backend, *_args, **_kwargs:
                        seen.setdefault("estimate", {"backend": backend}))

    voidscape._estimate_from_args(_args("recording.mp4"), {})

    assert seen["estimate"]["backend"] == "faster-whisper"


def test_guided_url_defaults_to_captions(monkeypatch):
    seen = {}
    monkeypatch.setattr(voidscape.video, "estimate",
                        lambda _inp, _frames, backend, *_args, **_kwargs:
                        seen.setdefault("estimate", {"backend": backend}))

    voidscape._estimate_from_args(_args("https://example.com/watch?v=1"), {})

    assert seen["estimate"]["backend"] == "captions"
