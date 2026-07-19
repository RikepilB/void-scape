import json
import subprocess
import sys
from pathlib import Path

import video


REPO = Path(__file__).resolve().parent.parent
CLI = REPO / "skill" / "scripts" / "video.py"


def _cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), *map(str, args)],
        capture_output=True, text=True, timeout=60,
    )


def test_manifest_describes_agent_contract(capsys):
    assert video.main(["manifest", "--compact"]) == 0
    manifest = json.loads(capsys.readouterr().out)

    assert manifest["protocol_version"] == "1.0"
    assert manifest["interactive"] is False
    assert set(manifest["commands"]) == {"manifest", "probe", "estimate", "run"}
    assert "--allow-cloud" in manifest["commands"]["run"]["flags"]
    assert "--allow-model-download" in manifest["commands"]["run"]["flags"]
    assert manifest["exit_codes"]["4"] == "approval_required"


def test_probe_supports_compact_standard_envelope(static_clip):
    result = _cli("probe", static_clip, "--envelope", "--compact")

    assert result.returncode == 0, result.stderr
    assert result.stdout.count("\n") == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["data"]["source"] == "local"
    assert payload["error"] is None
    assert payload["meta"] == {"command": "probe", "protocol_version": "1.0"}


def test_cloud_approval_error_has_deterministic_envelope_and_exit_code(static_clip, tmp_path):
    workdir = tmp_path / "blocked"
    result = _cli(
        "run", static_clip, "--tier", "audio", "--backend", "openai",
        "--workdir", workdir, "--envelope", "--compact",
    )

    assert result.returncode == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["data"] is None
    assert payload["error"]["code"] == "approval_required"
    assert payload["error"]["exit_code"] == 4
    assert payload["error"]["retryable"] is False
    assert "--allow-cloud" in payload["error"]["message"]
    assert not (workdir / "audio.mp3").exists()


def test_missing_input_has_input_error_exit_code(tmp_path):
    result = _cli("probe", tmp_path / "missing.mp4", "--envelope", "--compact")

    assert result.returncode == 3
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "input_error"
    assert payload["error"]["retryable"] is False


def test_corrupt_media_is_non_retryable_input_error(tmp_path):
    corrupt = tmp_path / "corrupt.mp4"
    corrupt.write_bytes(b"not a media file")

    result = _cli("probe", corrupt, "--envelope", "--compact")

    assert result.returncode == 3
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "input_error"
    assert payload["error"]["retryable"] is False


def test_rate_limit_operation_is_retryable():
    assert video._classify_error(RuntimeError("HTTP 429 rate limit")) == (
        6, "operation_failed", True,
    )


def test_usage_error_can_be_machine_readable():
    result = _cli("probe", "--not-a-real-flag", "--envelope", "--compact")

    assert result.returncode == 2
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "usage_error"
    assert payload["error"]["exit_code"] == 2


def test_legacy_probe_json_remains_compatible(static_clip):
    result = _cli("probe", static_clip)

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["source"] == "local"
    assert "ok" not in payload


def test_skill_documents_agent_machine_protocol():
    content = (REPO / "skill" / "SKILL.md").read_text(encoding="utf-8")
    for phrase in ("manifest --compact", "--envelope --compact", "retryable"):
        assert phrase in content
