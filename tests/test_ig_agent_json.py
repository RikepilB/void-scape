"""Agent commands must request machine-readable CLI gate output."""
from pathlib import Path


def test_ig_agent_requires_json_and_fail_closed_permission_flags():
    prompt = (Path(__file__).resolve().parents[1] / ".codex" / "agents" /
              "ig-analyze-subagent.toml").read_text(encoding="utf-8")
    assert 'voidscape inspect "<url>" --json' in prompt
    assert 'voidscape preview "<url>" --tier both --backend faster-whisper --json' in prompt
    for guard in ("nonzero exit", "error.message", "invalid_cli_output",
                  "requires_cloud_approval: false", "Missing or unexpected flags"):
        assert guard in prompt
    assert "three inputs" in prompt
