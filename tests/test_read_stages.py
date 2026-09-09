"""Partial evidence remains usable without becoming a successful read."""
import json
from pathlib import Path

import pytest

import article
import chat
import image
import video
import voidscape


def _probe(inp):
    return {"source": "local", "input": inp, "sidecar_transcript": None,
            "captions_available": False, "duration_s": 10.0, "width": 640,
            "height": 360, "fps": 30.0, "has_audio": True}


def _frames(media, root, *args, **kwargs):
    path = root / "frame.jpg"
    path.write_bytes(b"synthetic frame")
    return [{"file": str(path), "t": 0}], 0


@pytest.mark.parametrize("guided", [False, True])
def test_transcript_failure_preserves_frames_and_fails_read(tmp_path, monkeypatch, capsys, guided):
    monkeypatch.setattr(video, "probe", _probe)
    monkeypatch.setattr(video, "_extract_frames", _frames)

    def fail(*args, **kwargs):
        raise RuntimeError("synthetic backend failure")

    monkeypatch.setattr(video, "_transcribe", fail)
    if guided:
        monkeypatch.setattr(voidscape, "_load_workspace", lambda *args: {})
        monkeypatch.setattr(voidscape, "_estimate_from_args", lambda *args: {
            "tier": "both", "backend": "captions", "requires_cloud_approval": False,
            "needs_model_download": False, "needs_install": False})
        code = voidscape.main(["read", "clip.mp4", "--workdir", str(tmp_path), "--json"])
    else:
        code = video.main(["run", "clip.mp4", "--workdir", str(tmp_path), "--envelope"])
    output = json.loads(capsys.readouterr().out)
    assert code == 6
    assert output["ok"] is False
    assert output["meta"]["failed_stage"] == "transcribe"
    assert output["meta"]["manifest_written"] is True
    assert "frames" in output["meta"]["stages_completed"]
    assert "transcribe" not in output["meta"]["stages_completed"]
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert output["data"] == manifest
    assert manifest["status"] == "partial"
    assert manifest["tier"] == "both"
    assert manifest["transcript"] is None
    assert manifest["warnings"][0]["code"] == "read_incomplete"
    assert (tmp_path / "frame.jpg").is_file()
    assert not (tmp_path / ".agent/latest-read.json").exists()


def test_image_copy_failure_lists_only_completed_items(tmp_path, monkeypatch):
    source = tmp_path / "source.jpg"
    source.write_bytes(b"fixture")
    monkeypatch.setattr(image, "probe", lambda inp: {
        "kind": "carousel", "source": "local", "input": inp, "item_count": 2, "skipped": [],
        "images": [{"index": i, "source_name": f"{i}.jpg", "source": str(source),
                    "width": 1, "height": 1, "bytes": 7} for i in (1, 2)]})
    original = image.shutil.copy2

    def copy_one(source, target):
        if target.name.startswith("002"):
            raise OSError("copy failed")
        return original(source, target)

    monkeypatch.setattr(image.shutil, "copy2", copy_one)
    root = tmp_path / "output"
    with pytest.raises(RuntimeError) as caught:
        image.run("input", str(root))
    output = video.failure_envelope(caught.value, "run")
    assert output["meta"]["failed_stage"] == "copy"
    assert output["data"]["item_count"] == 1
    assert len(output["data"]["images"]) == 1
    assert output["data"]["status"] == "partial"
    assert not (root / ".agent").exists()


def test_article_failure_preserves_completed_entries(tmp_path, monkeypatch):
    source = tmp_path / "feed.xml"
    source.write_text('<rss><channel><title>Fixture</title><item><title>One</title><description>First</description></item>'
                      '<item><title>Two</title><description>Second</description></item></channel></rss>', encoding="utf-8")
    original = Path.write_text

    def fail_second(path, *args, **kwargs):
        if path.name.startswith("002-"):
            raise OSError("entry failure")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_second)
    with pytest.raises(RuntimeError) as caught:
        article.run(str(source), str(tmp_path / "output"))
    output = video.failure_envelope(caught.value, "run")
    assert output["meta"]["failed_stage"] == "write_entries"
    assert output["data"]["item_count"] == 1
    assert output["data"]["status"] == "partial"


def test_chat_manifest_failure_preserves_original_error(tmp_path, monkeypatch):
    source = tmp_path / "chat.txt"
    source.write_text("[05/12/24, 10:15:41] Fixture: hello\n[05/12/24, 10:16:00] Other: reply\n", encoding="utf-8")
    original = Path.open

    def fail_manifest(path, *args, **kwargs):
        if path.name == "manifest.json":
            raise OSError("synthetic disk full")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_manifest)
    with pytest.raises(RuntimeError, match="manifest write failed") as caught:
        chat.run(str(source), str(tmp_path / "output"))
    output = video.failure_envelope(caught.value, "run")
    assert output["meta"]["failed_stage"] == "manifest"
    assert output["meta"]["manifest_written"] is False
    assert "write_transcript" in output["meta"]["stages_completed"]
    assert output["meta"]["warnings"][-1]["code"] == "partial_manifest_unavailable"
    assert (tmp_path / "output/messages.txt").is_file()


def test_gate_refusal_has_no_partial_manifest_or_warning(tmp_path, monkeypatch):
    monkeypatch.setattr(video, "probe", _probe)
    monkeypatch.setattr(video, "_extract_frames", lambda *args, **kwargs: pytest.fail("frames before consent"))
    with pytest.raises(video.ApprovalRequired) as caught:
        video.run("clip.mp4", backend="groq", workdir=str(tmp_path))
    output = video.failure_envelope(caught.value, "run")
    assert output["error"]["exit_code"] == 4
    assert output["meta"]["failed_stage"] == "validate"
    assert output["meta"]["warnings"] == []
    assert output["data"] is None
    assert not list(tmp_path.iterdir())


def test_success_warnings_survive_manifest_and_context_is_cleared(tmp_path, monkeypatch):
    monkeypatch.setattr(video, "probe", _probe)

    def transcribe(*args, **kwargs):
        video._read_warning("transcription_gap", "transcribe", "One synthetic chunk is missing.")
        path = tmp_path / "transcript.txt"
        path.write_text("[00:00] available evidence", encoding="utf-8")
        return str(path), "available evidence"

    monkeypatch.setattr(video, "_transcribe", transcribe)
    result = video.run("clip.mp4", tier="audio", workdir=str(tmp_path))
    assert result["status"] == "complete"
    assert result["warnings"][0]["code"] == "transcription_gap"
    assert json.loads((tmp_path / "manifest.json").read_text())["warnings"] == result["warnings"]
    assert video._envelope(result, None, "run")["meta"]["warnings"] == result["warnings"]
    assert video._ACTIVE_READ.get() is None


def test_partial_manifest_cannot_get_success_pointer(tmp_path):
    with pytest.raises(ValueError, match="completed read"):
        video.write_read_pointer({"workdir": str(tmp_path), "status": "partial"})
    assert not (tmp_path / ".agent").exists()


def test_unconfined_partial_artifacts_are_not_exposed(tmp_path, monkeypatch):
    outside = tmp_path / "outside.jpg"
    outside.write_bytes(b"private fixture")
    root = tmp_path / "output"
    monkeypatch.setattr(video, "probe", _probe)
    monkeypatch.setattr(video, "_extract_frames", lambda *args, **kwargs: ([{"file": str(outside), "t": 0}], 0))

    def fail(*args, **kwargs):
        raise RuntimeError("original backend failure")

    monkeypatch.setattr(video, "_transcribe", fail)
    with pytest.raises(RuntimeError, match="original backend") as caught:
        video.run("clip.mp4", workdir=str(root))
    output = video.failure_envelope(caught.value, "run")
    assert output["data"] is None
    assert str(outside) not in json.dumps(output)
    assert not (root / "manifest.json").exists()


def test_clean_success_and_probe_failure_report_actual_stages(tmp_path, monkeypatch):
    source = tmp_path / "article.md"
    source.write_text("# Fixture\n\nLocal article body.", encoding="utf-8")
    result = article.run(str(source), str(tmp_path / "output"))
    assert result["status"] == "complete"
    assert result["warnings"] == []
    assert result["stages_completed"] == ["probe", "validate", "workdir", "write_entries", "manifest"]
    with pytest.raises(FileNotFoundError) as caught:
        article.run(str(tmp_path / "missing.md"))
    assert video.failure_envelope(caught.value, "run")["meta"]["failed_stage"] == "probe"


@pytest.mark.parametrize("all_failed", [False, True])
def test_chunk_failures_produce_real_coverage_warning(tmp_path, monkeypatch, all_failed):
    monkeypatch.setattr(video, "probe", _probe)
    monkeypatch.setattr(video, "_to_audio", lambda *args, **kwargs: "audio.wav")
    monkeypatch.setattr(video, "_split_audio", lambda *args: [("one.wav", 0), ("two.wav", 5)])

    def request(backend, path):
        if all_failed or path == "two.wav":
            raise RuntimeError("synthetic chunk failure")
        return {"text": "available speech"}

    monkeypatch.setattr(video, "_api_request", request)
    if all_failed:
        with pytest.raises(video.BackendFailures) as caught:
            video.run("clip.mp4", tier="audio", backend="groq", allow_cloud=True, workdir=str(tmp_path))
        output = video.failure_envelope(caught.value, "run")
        assert output["error"]["exit_code"] == 6
        assert output["meta"]["failed_stage"] == "transcribe"
        assert output["data"] is None
        assert not (tmp_path / "manifest.json").exists()
    else:
        result = video.run("clip.mp4", tier="audio", backend="groq", allow_cloud=True, workdir=str(tmp_path))
        assert result["warnings"] == [{"code": "transcription_gap", "stage": "transcribe",
                                       "detail": "1 of 2 audio chunks could not be transcribed."}]


def test_pointer_failure_keeps_complete_manifest(tmp_path, monkeypatch):
    source = tmp_path / "article.md"
    source.write_text("# Fixture\n\nEvidence.", encoding="utf-8")
    root = tmp_path / "output"

    def fail_pointer(*args):
        raise OSError("recovery storage failure")

    monkeypatch.setattr(video, "write_read_pointer", fail_pointer)
    with pytest.raises(OSError) as caught:
        article.run(str(source), str(root))
    output = video.failure_envelope(caught.value, "run")
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "complete"
    assert output["data"] == manifest
    assert output["meta"]["failed_stage"] == "recovery"
    assert output["meta"]["manifest_written"] is True
