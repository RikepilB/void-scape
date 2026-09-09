"""Agent commands must request machine-readable CLI gate output."""
from pathlib import Path
import re


def test_ig_agent_requires_json_and_fail_closed_permission_flags():
    prompt = (Path(__file__).resolve().parents[1] / ".codex" / "agents" /
              "ig-analyze-subagent.toml").read_text(encoding="utf-8")
    assert 'voidscape inspect "<url>" --json' in prompt
    assert 'voidscape preview "<url>" --tier both --backend faster-whisper --json' in prompt
    for guard in ("nonzero exit", "error.message", "invalid_cli_output",
                  "requires_cloud_approval: false", "Missing or unexpected flags"):
        assert guard in prompt
    assert "three inputs" in prompt


def test_ig_agent_retains_evidence_and_never_receives_credentials():
    prompt = (Path(__file__).resolve().parents[1] / ".codex" / "agents" /
              "ig-analyze-subagent.toml").read_text(encoding="utf-8")
    assert "`evidence_dir`" in prompt
    for obsolete in ("cookies_path", "READ_VIDEO_YTDLP_COOKIES", "Delete the temp workdir",
                     "with the raw error text", "any file present, note or marker"):
        assert obsolete not in prompt
    assert "Preserve the evidence directory" in prompt
    assert "A skip marker records an attempt, not permanent completion" in prompt
    assert "never store approvals" in prompt
    read_command = re.search(r'voidscape read.*?--json', prompt, re.DOTALL)
    assert read_command is not None
    assert 'partial result, or deliberate stop' in prompt
    assert 'A partial or skip result cannot authorize an unsave' in prompt


def test_capture_scope_and_readiness_are_explicit():
    prompt = (Path(__file__).resolve().parents[1] / ".codex" / "agents" /
              "instagram-capture-subagent.toml").read_text(encoding="utf-8")
    assert "collection_name" in prompt
    assert "do not pick a default" in prompt
    assert 'named "Cursos"' not in prompt
    assert "malformed JSON" in prompt
    assert "queue readiness only" in prompt
    assert "verified note artifact" in prompt
