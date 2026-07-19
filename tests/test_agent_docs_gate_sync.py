"""Codex agent docs that drive video.py must describe both approval gates."""
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOCS = [
    REPO / ".codex" / "agents" / "ig-analyze-subagent.toml",
    REPO / ".codex" / "agents" / "instagram-capture-subagent.toml",
]


def test_codex_agent_docs_mention_model_download_gate():
    missing = [d for d in DOCS if "needs_model_download" not in d.read_text(encoding="utf-8")]
    assert not missing, f"docs missing needs_model_download handling: {missing}"
