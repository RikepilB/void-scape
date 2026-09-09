"""Gate metadata distinguishes user action without disclosing credential values."""
import json

import pytest

import article
import video
import voidscape


def _info(inp):
    return {"source": "local", "input": inp, "sidecar_transcript": None,
            "captions_available": False, "duration_s": 10.0, "width": 640,
            "height": 360, "fps": 30.0, "has_audio": True}


@pytest.mark.parametrize("backend", sorted(video.CLOUD_BACKENDS))
def test_cloud_gate_precedes_credentials(monkeypatch, backend):
    monkeypatch.setattr(video, "probe", _info)
    previous_get = video.os.environ.get

    def forbid_keys(name, default=None):
        if name.endswith("API_KEY"):
            pytest.fail("credential lookup preceded cloud approval")
        return previous_get(name, default)

    monkeypatch.setattr(video.os.environ, "get", forbid_keys)
    preview = video.estimate("clip.mp4", tier="audio", backend=backend)
    assert preview["gate"] == {"type": "cloud_approval", "backend": backend}
    with pytest.raises(video.ApprovalRequired) as caught:
        video.run("clip.mp4", tier="audio", backend=backend)
    error = video._error_payload(caught.value)
    assert error["exit_code"] == 4
    assert error["gate"] == preview["gate"]


def test_model_download_gate_has_distinct_type(monkeypatch):
    monkeypatch.setattr(video, "probe", _info)
    monkeypatch.setattr(video, "_model_download_info", lambda *args: {"status": "required", "model": "small"})
    with pytest.raises(video.ApprovalRequired) as caught:
        video.run("clip.mp4", tier="audio", backend="faster-whisper")
    error = video._error_payload(caught.value)
    assert error["exit_code"] == 4
    assert error["gate"] == {"type": "model_download", "backend": "faster-whisper"}


@pytest.mark.parametrize("backend", sorted(video.CLOUD_BACKENDS))
def test_missing_credentials_report_only_environment_name(monkeypatch, backend):
    monkeypatch.setattr(video.os.environ, "get", lambda *args: None)
    with pytest.raises(video.BackendGateError) as caught:
        if backend == "gemini":
            video._gemini("unused.wav")
        else:
            video._api_request(backend, "unused.wav")
    error = video._error_payload(caught.value)
    assert error["exit_code"] == 5
    assert error["gate"]["type"] == "missing_credentials"
    assert error["gate"]["backend"] == backend
    assert error["gate"]["env_var"].endswith("API_KEY")
    assert set(error["gate"]) == {"type", "backend", "env_var"}


def test_raw_and_guided_error_payloads_match(monkeypatch, capsys):
    failure = video.BackendGateError("GROQ_API_KEY not set", "missing_credentials", "groq", "GROQ_API_KEY")

    def fail(*args, **kwargs):
        raise failure

    monkeypatch.setattr(video, "run", fail)
    assert video.main(["run", "unused.mp4", "--envelope"]) == 5
    raw = json.loads(capsys.readouterr().out)
    assert voidscape._print_error(failure, True) == 5
    guided = json.loads(capsys.readouterr().out)
    assert raw["error"] == guided["error"]


def test_approved_read_reaches_credentials_without_upload(tmp_path, monkeypatch):
    monkeypatch.setattr(video, "probe", _info)
    monkeypatch.setattr(video.os.environ, "get", lambda *args: None)
    monkeypatch.setattr(video, "_to_audio", lambda *args, **kwargs: "unused.wav")
    monkeypatch.setattr(video, "_split_audio", lambda *args: [("unused.wav", 0)])
    monkeypatch.setattr(video, "urlopen", lambda *args, **kwargs: pytest.fail("upload without a key"))
    with pytest.raises(video.BackendGateError) as caught:
        video.run("clip.mp4", tier="audio", backend="groq", allow_cloud=True, workdir=str(tmp_path))
    assert video._error_payload(caught.value)["gate"]["type"] == "missing_credentials"
    assert not (tmp_path / "manifest.json").exists()
    assert not (tmp_path / ".agent/latest-read.json").exists()


def test_late_model_failure_preserves_operation_exit():
    error = video._error_payload(video.BackendGateError(
        "model is not cached; explicit user consent required", "model_download", "faster-whisper"))
    assert error["exit_code"] == 6
    assert error["gate"]["type"] == "model_download"


def test_mixed_fallback_failures_preserve_gates_without_single_cause(tmp_path, monkeypatch):
    def fail(*args):
        backend = args[4]
        if backend == "groq":
            raise video.BackendGateError("GROQ_API_KEY not set", "missing_credentials", backend, "GROQ_API_KEY")
        raise RuntimeError("backend unavailable")

    monkeypatch.setattr(video, "_transcribe_one", fail)
    with pytest.raises(video.BackendFailures) as caught:
        video._transcribe("unused.mp4", _info("unused.mp4"), None, tmp_path, "groq,openai")
    error = video._error_payload(caught.value)
    assert "gate" not in error
    assert error["gates"] == [{"type": "missing_credentials", "backend": "groq", "env_var": "GROQ_API_KEY"}]


def test_article_gate_uses_same_contract(capsys):
    assert article.main(["run", "https://example.com/article", "--envelope"]) == 4
    error = json.loads(capsys.readouterr().out)["error"]
    assert error["gate"] == {"type": "cloud_approval", "backend": "article_fetch"}


def test_provider_exception_cannot_inject_gate_metadata():
    failure = RuntimeError("provider failure")
    failure.gate = {"type": "missing_credentials", "env_var": "PRIVATE_VALUE"}
    error = video._error_payload(video.BackendFailures("all failed", [failure]))
    assert "gates" not in error
    assert "PRIVATE_VALUE" not in json.dumps(error)
