"""Deliberate stops preserve intent without executing downstream operations."""
import json

import pytest
import video
import voidscape


def probe(inp):
    return {"input": inp, "source": "local", "duration_s": 10.0,
            "width": 640, "height": 360, "sidecar_transcript": None,
            "captions_available": False}


def forbidden(*args, **kwargs):
    pytest.fail("downstream operation executed")


@pytest.mark.parametrize("stop_at", ["probe", "frames"])
@pytest.mark.parametrize("guided", [False, True])
def test_stop_extent_and_recovery(tmp_path, monkeypatch, capsys, stop_at, guided):
    monkeypatch.setattr(video, "probe", probe)
    monkeypatch.setattr(video, "_transcribe", forbidden)
    monkeypatch.setattr(video, "_have_local_backend", forbidden)
    monkeypatch.setattr(video, "_model_available_locally", forbidden)
    monkeypatch.setattr(video, "_download", forbidden)
    monkeypatch.setattr(voidscape, "_load_workspace", lambda *args: {})

    def frames(media, root, *args, **kwargs):
        assert stop_at == "frames"
        path = root / "frame.jpg"
        path.write_bytes(b"synthetic frame")
        return [{"file": str(path), "t": 0}], 0

    monkeypatch.setattr(video, "_extract_frames", frames)
    args = ["clip.mp4", "--stop-at", stop_at, "--backend", "groq,faster-whisper",
            "--workdir", str(tmp_path)]
    code = (voidscape.main(["read", *args, "--json"]) if guided
            else video.main(["run", *args, "--envelope"]))
    output = json.loads(capsys.readouterr().out)
    assert code == 0
    result = output if guided else output["data"]
    if not guided:
        assert output["ok"] is True
        assert output["meta"]["stopped_at"] == stop_at
    assert result["status"] == "stopped"
    assert result["stopped_by"] == "user"
    assert result["requested_tier"] == result["tier"] == "both"
    assert result["requested_backend"] == "groq,faster-whisper"
    assert result["backend"] == "none"
    assert result["transcript"] is None
    assert "transcribe" not in result["stages_completed"]
    assert ("frames" in result["stages_completed"]) == (stop_at == "frames")
    pointer = json.loads((tmp_path / ".agent/latest-read.json").read_text())
    assert pointer["status"] == "stopped"
    assert pointer["stop_at"] == stop_at
    assert len(pointer["evidence"]) == (stop_at == "frames")
    assert json.loads((tmp_path / "manifest.json").read_text()) == result


@pytest.mark.parametrize("stop_at", ["probe", "frames"])
def test_preview_prices_only_executed_extent(monkeypatch, stop_at):
    monkeypatch.setattr(video, "probe", probe)
    monkeypatch.setattr(video, "_have_local_backend", forbidden)
    monkeypatch.setattr(video, "_model_available_locally", forbidden)
    estimate = video.estimate("clip.mp4", backend="groq,faster-whisper", stop_at=stop_at)
    assert estimate["cost_usd"]["transcription"] == 0
    assert estimate["tokens"]["transcript"] == 0
    assert estimate["requires_cloud_approval"] is False
    assert estimate["needs_model_download"] is False
    assert estimate["needs_install"] is False
    assert estimate["gate"] is None
    assert (estimate["frames"] > 0) == (stop_at == "frames")


@pytest.mark.parametrize("command", ["preview", "read"])
@pytest.mark.parametrize("reader", ["image", "article", "chat"])
def test_other_readers_reject_before_output(tmp_path, monkeypatch, capsys, command, reader):
    monkeypatch.setattr(voidscape, "_load_workspace", lambda *args: {})
    monkeypatch.setattr(video, "probe", forbidden)
    args = [command, "unused", "--reader", reader, "--stop-at", "probe", "--json"]
    if command == "read":
        args += ["--workdir", str(tmp_path / "output")]
    assert voidscape.main(args) == 3
    assert "only by the video/audio reader" in capsys.readouterr().out
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("operation", [video.run, video.estimate])
@pytest.mark.parametrize("tier,stop_at", [("audio", "frames"), ("both", "invalid")])
def test_invalid_extent_rejected_before_probe(monkeypatch, operation, tier, stop_at):
    monkeypatch.setattr(video, "probe", forbidden)
    with pytest.raises(ValueError):
        operation("unused", tier=tier, stop_at=stop_at)


def test_full_read_still_requires_cloud_consent(tmp_path, monkeypatch):
    monkeypatch.setattr(video, "probe", probe)
    monkeypatch.setattr(video, "_transcribe", forbidden)
    with pytest.raises(video.ApprovalRequired):
        video.run("clip.mp4", backend="groq", workdir=str(tmp_path / "output"))
    assert not (tmp_path / "output").exists()


def test_frame_failure_does_not_become_successful_stop(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(video, "probe", probe)
    def fail(*args, **kwargs):
        raise RuntimeError("synthetic extraction failure")
    monkeypatch.setattr(video, "_extract_frames", fail)
    assert video.main(["run", "clip.mp4", "--stop-at", "frames",
                       "--workdir", str(tmp_path), "--envelope"]) == 6
    result = json.loads(capsys.readouterr().out)
    assert result["ok"] is False
    assert result["meta"]["failed_stage"] == "frames"
    assert "stopped_at" not in result["meta"]
    assert not (tmp_path / ".agent/latest-read.json").exists()


def test_probe_stop_accepts_unknown_duration(tmp_path, monkeypatch):
    monkeypatch.setattr(video, "probe", lambda inp: {**probe(inp), "duration_s": None})
    result = video.run("clip.mp4", stop_at="probe", workdir=str(tmp_path))
    assert result["status"] == "stopped"
    assert result["source_info"]["duration_s"] is None


def test_executed_acquisition_permission_is_not_bypassed(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(video, "probe", lambda inp: {**probe(inp), "source": "url"})
    monkeypatch.setattr(video, "resolve_input", lambda inp: inp)
    def denied(*args, **kwargs):
        raise PermissionError("synthetic acquisition permission required")
    monkeypatch.setattr(video, "_download", denied)
    monkeypatch.setattr(video, "_extract_frames", forbidden)
    assert video.main(["run", "https://example.com/clip.mp4", "--stop-at", "frames",
                       "--workdir", str(tmp_path), "--envelope"]) == 4
    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is False
    assert output["data"] is None
    assert output["meta"]["failed_stage"] == "acquire"
    assert not (tmp_path / "manifest.json").exists()


def test_full_read_still_requires_model_download_consent(tmp_path, monkeypatch):
    monkeypatch.setattr(video, "probe", probe)
    monkeypatch.setattr(video, "_model_download_info", lambda *args: {
        "status": "required", "model": "synthetic-model"})
    monkeypatch.setattr(video, "_transcribe", forbidden)
    with pytest.raises(video.ApprovalRequired) as error:
        video.run("clip.mp4", backend="faster-whisper", workdir=str(tmp_path / "output"))
    assert error.value.gate["type"] == "model_download"
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("guided", [False, True])
def test_preview_cli_discloses_selected_extent(monkeypatch, capsys, guided):
    monkeypatch.setattr(video, "probe", probe)
    monkeypatch.setattr(voidscape, "_load_workspace", lambda *args: {})
    args = ["clip.mp4", "--stop-at", "probe", "--backend", "groq"]
    code = (voidscape.main(["preview", *args, "--json"]) if guided
            else video.main(["estimate", *args, "--envelope"]))
    output = json.loads(capsys.readouterr().out)
    data = output if guided else output["data"]
    assert code == 0
    assert data["stop_at"] == "probe"
    assert data["requested_backend"] == "groq"
    assert data["frames"] == 0
    assert data["tokens"]["transcript"] == 0
