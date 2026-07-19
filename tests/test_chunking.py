from pathlib import Path

import pytest

import video
from conftest import requires_ffmpeg


@requires_ffmpeg
def test_small_file_passes_through(tone_mp3):
    assert video._split_audio(str(tone_mp3)) == [(str(tone_mp3), 0.0)]


@requires_ffmpeg
def test_oversized_file_splits_under_cap(tone_mp3, tmp_path):
    work = tmp_path / "audio.mp3"
    work.write_bytes(tone_mp3.read_bytes())
    cap = work.stat().st_size // 3                 # force >= 3 chunks from the 30s tone
    chunks = video._split_audio(str(work), max_bytes=cap)
    assert len(chunks) >= 3
    for path, _off in chunks:
        assert Path(path).stat().st_size <= cap * 1.15   # segment split is approximate; small slack


@requires_ffmpeg
def test_offsets_accumulate_to_duration(tone_mp3, tmp_path):
    work = tmp_path / "audio.mp3"
    work.write_bytes(tone_mp3.read_bytes())
    cap = work.stat().st_size // 3
    chunks = video._split_audio(str(work), max_bytes=cap)
    assert chunks[0][1] == 0.0
    offs = [off for _p, off in chunks]
    assert offs == sorted(offs)
    total = chunks[-1][1] + video._audio_duration(chunks[-1][0])
    assert total == pytest.approx(30.0, abs=1.5)


def seg_response(*starts_texts):
    return {"segments": [{"start": s, "text": t} for s, t in starts_texts]}


def test_resp_to_text_shifts_offsets():
    out = video._resp_to_text(seg_response((0.0, "hello"), (65.0, "world")), offset=120.0)
    assert out.splitlines() == ["[02:00] hello", "[03:05] world"]


def test_chunked_transcribe_merges_with_shifts(monkeypatch, tmp_path):
    a = tmp_path / "audio.mp3"
    a.write_bytes(b"x")
    monkeypatch.setattr(video, "_split_audio",
                        lambda audio, max_bytes=video._API_UPLOAD_CAP:
                        [(str(a), 0.0), (str(a), 100.0)])
    responses = iter([seg_response((1.0, "one")), seg_response((2.0, "two"))])
    monkeypatch.setattr(video, "_api_request", lambda b, p: next(responses))
    out = video._api_transcribe("groq", str(a))
    assert out.splitlines() == ["[00:01] one", "[01:42] two"]


def test_partial_chunk_failure_leaves_gap_marker(monkeypatch, tmp_path, capsys):
    a = tmp_path / "audio.mp3"
    a.write_bytes(b"x")
    monkeypatch.setattr(video, "_split_audio",
                        lambda audio, max_bytes=video._API_UPLOAD_CAP:
                        [(str(a), 0.0), (str(a), 100.0), (str(a), 200.0)])
    calls = {"n": 0}

    def fake_request(backend, path):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("HTTP 500")
        return seg_response((0.0, f"part{calls['n']}"))

    monkeypatch.setattr(video, "_api_request", fake_request)
    out = video._api_transcribe("groq", str(a))
    lines = out.splitlines()
    assert lines[0] == "[00:00] part1"
    assert "transcription gap: chunk 2 of 3" in lines[1]
    assert lines[2] == "[03:20] part3"


def test_all_chunks_fail_raises(monkeypatch, tmp_path):
    a = tmp_path / "audio.mp3"
    a.write_bytes(b"x")
    monkeypatch.setattr(video, "_split_audio",
                        lambda audio, max_bytes=video._API_UPLOAD_CAP:
                        [(str(a), 0.0), (str(a), 100.0)])

    def boom(backend, path):
        raise RuntimeError("HTTP 500")

    monkeypatch.setattr(video, "_api_request", boom)
    import pytest as _pytest
    with _pytest.raises(RuntimeError, match="all 2 chunks failed"):
        video._api_transcribe("groq", str(a))
