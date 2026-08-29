"""Truth guards for the agent-facing documentation tree (issues #18-#22)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import article
import image
import video


REPO = Path(__file__).resolve().parent.parent
AGENT_DOCS = REPO / "docs" / "agents"
AGENT_INDEX = AGENT_DOCS / "index.md"
AGENT_MANIFEST = AGENT_DOCS / "manifest.json"
ROADMAP_STATUS = AGENT_DOCS / "roadmap-status.md"
IA_SPEC = (
    REPO / "docs" / "superpowers" / "specs"
    / "2026-08-29-agent-docs-information-architecture.md"
)
BROWSER_BRIDGE_SPEC = (
    REPO / "docs" / "superpowers" / "specs"
    / "2026-08-28-harness-neutral-browser-bridge-design.md"
)

REQUIRED_MARKDOWN = {
    "index.md",
    "harnesses.md",
    "workflow.md",
    "constraints.md",
    "automation.md",
    "observe-and-capture.md",
    "roadmap-status.md",
    "references.md",
    "readers/images.md",
    "readers/video-audio.md",
    "readers/articles-rss.md",
    "capture-adapters/instagram.md",
    "capture-adapters/youtube.md",
}
STATUS_VALUES = {"shipped", "dev-only", "planned"}
GATE_FIELDS = {
    "requires_cloud_approval",
    "needs_model_download",
    "needs_install",
    "free",
}
OFFICIAL_HARNESS_URLS = {
    "https://developers.openai.com/codex/chrome-extension/",
    "https://developers.openai.com/codex/remote-connections/",
    "https://developers.openai.com/codex/app/browser/",
    "https://docs.anthropic.com/en/docs/claude-code/chrome",
    "https://docs.anthropic.com/en/docs/claude-code/remote-control",
}


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(text: str) -> str:
    return " ".join(text.split())


def _reader_manifest(module) -> dict:
    return module._cli_manifest()


def _relative_markdown_links(path: Path):
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", _text(path)):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        yield target.split("#", 1)[0]


def test_required_agent_docs_and_manifest_exist():
    existing = {
        path.relative_to(AGENT_DOCS).as_posix()
        for path in AGENT_DOCS.rglob("*.md")
    }
    assert REQUIRED_MARKDOWN <= existing
    assert AGENT_MANIFEST.is_file()


def test_information_architecture_maps_every_page_to_sources():
    spec = _text(IA_SPEC)
    for relative in REQUIRED_MARKDOWN - {"observe-and-capture.md"}:
        assert f"`{relative}`" in spec
    for canonical in (
        "skill/SKILL.md",
        "docs/harness-support.md",
        "docs/ROADMAP.md",
        "docs/architecture.md",
    ):
        assert canonical in spec


def test_all_relative_agent_doc_links_resolve():
    broken = []
    for page in AGENT_DOCS.rglob("*.md"):
        for target in _relative_markdown_links(page):
            resolved = (page.parent / target).resolve()
            if not resolved.exists():
                broken.append((page.relative_to(REPO).as_posix(), target))
    assert not broken, f"broken agent-doc links: {broken}"


def test_readme_and_landing_page_link_the_agent_docs_hub():
    assert "[Agent documentation](docs/agents/index.md)" in _text(REPO / "README.md")
    landing = _text(REPO / "docs" / "index.html")
    assert 'href="agents/index.md">Agent docs</a>' in landing


def test_harness_matrix_uses_official_links_and_evidence_labels():
    harnesses = _text(AGENT_DOCS / "harnesses.md")
    references = _text(AGENT_DOCS / "references.md")
    for url in OFFICIAL_HARNESS_URLS:
        assert url in harnesses or url in references
    for label in ("personally-tested", "vendor-documented", "unverified"):
        assert label in harnesses
    assert "A vendor feature is not automatically a Voidscape capability" in _normalized(
        _text(AGENT_INDEX)
    )


def test_agent_docs_preserve_workflow_gates_and_citation_contracts():
    workflow = _text(AGENT_DOCS / "workflow.md")
    constraints = _text(AGENT_DOCS / "constraints.md")
    for required in (
        "inspect -> preview -> read",
        "requires_cloud_approval",
        "needs_model_download",
        "needs_install",
        "`free`",
        "--allow-cloud",
        "--allow-model-download",
        "[image N]",
        "[MM:SS]",
        "[article N]",
        "[entry N]",
    ):
        assert required in workflow or required in constraints


def test_agent_docs_forbid_browser_state_and_implicit_approval():
    combined = "\n".join(_text(path) for path in AGENT_DOCS.rglob("*.md"))
    lowered = combined.casefold()
    assert "never reads browser credentials, cookies, storage, or secrets" in lowered
    assert "the manifest never grants approvals" in lowered
    for forbidden_claim in (
        "voidscape reads browser cookies",
        "voidscape exports browser storage",
        "browser login transfers to the cli",
        "automatic cookie transfer is supported",
        "zero prompts guaranteed",
    ):
        assert forbidden_claim not in lowered


def test_manifest_matches_reader_protocol_and_known_entry_points():
    manifest = json.loads(_text(AGENT_MANIFEST))
    reader_manifests = [_reader_manifest(module) for module in (video, image, article)]

    assert manifest["schema_version"] == "1.0"
    assert manifest["protocol"]["version"] == "1.0"
    assert {item["protocol_version"] for item in reader_manifests} == {"1.0"}
    assert manifest["protocol"]["exit_codes"] == reader_manifests[0]["exit_codes"]
    assert set(manifest["gate_fields"]) == GATE_FIELDS

    for entry in manifest["entry_points"]:
        assert entry["status"] in STATUS_VALUES
        if entry["status"] != "planned":
            assert (REPO / entry["path"]).is_file()
    for capability in manifest["capabilities"]:
        assert capability["status"] in STATUS_VALUES


def test_manifest_names_installed_skills_and_citation_contracts():
    manifest = json.loads(_text(AGENT_MANIFEST))
    skills = {item["name"]: item["role"] for item in manifest["installed_skills"]}
    assert skills == {"voidscape": "primary", "read-video": "backward_compatibility"}
    assert manifest["install_roots"] == ["~/.codex/skills/", "~/.agents/skills/"]
    assert manifest["citation_contracts"] == {
        "image": "[image N]",
        "video_audio": "[MM:SS]",
        "article": "[article N]",
        "rss_atom": "[entry N]",
    }
    assert manifest["security"] == {
        "browser_state_access": False,
        "browser_auth_transfers_to_cli": False,
        "approval_flags_must_be_explicit": True,
        "per_job_cloud_approval": True,
        "separate_model_download_approval": True,
    }


def test_shipped_dev_only_and_planned_statuses_match_main():
    manifest = json.loads(_text(AGENT_MANIFEST))
    statuses = {item["id"]: item["status"] for item in manifest["capabilities"]}
    assert statuses["workflow.guided_read"] == "shipped"
    assert statuses["evidence.image_carousel"] == "shipped"
    assert statuses["evidence.video_audio"] == "shipped"
    assert statuses["evidence.article"] == "shipped"
    assert statuses["capture.instagram_queue"] == "dev-only"
    assert statuses["capture.youtube_private_playlist"] == "dev-only"
    assert statuses["capture.observe_on_demand"] == "planned"
    assert statuses["integration.mcp_host"] == "planned"
    assert statuses["integration.browser_bridge"] == "planned"

    roadmap = _text(ROADMAP_STATUS)
    assert "| Thin observe CLI | `planned` |" in roadmap
    assert "| Production universal browser extension | `parked` |" in roadmap
    assert "| Unattended orchestration | `parked` |" in roadmap


def test_capture_adapter_pages_do_not_call_dev_tools_installed_commands():
    instagram = _text(AGENT_DOCS / "capture-adapters" / "instagram.md")
    youtube = _text(AGENT_DOCS / "capture-adapters" / "youtube.md")
    for page in (instagram, youtube):
        assert "**Status:** `dev-only`" in page
        assert "Installed" in page
        assert "`planned`" in page
    assert "not included by the skill installer" in _normalized(instagram).casefold()
    assert "not included by the skill installer" in _normalized(youtube).casefold()


def test_observe_playbook_keeps_capture_external_and_gates_per_job():
    playbook = _text(AGENT_DOCS / "observe-and-capture.md")
    normalized = _normalized(playbook)
    matrix = _text(REPO / "docs" / "chrome-use-case-matrix.md")
    for required in (
        "Voidscape does not currently ship the capture command",
        "It is not a Voidscape dependency",
        "The harness never exports the file",
        "Cloud transcription",
        "Local model download",
    ):
        assert required in normalized
    assert "## Observe-and-capture scenarios" in matrix
    assert matrix.split("## Observe-and-capture scenarios", 1)[1].count("| ") >= 5


def test_browser_bridge_and_mcp_remain_design_only():
    spec = _text(BROWSER_BRIDGE_SPEC)
    manifest = json.loads(_text(AGENT_MANIFEST))
    statuses = {item["id"]: item["status"] for item in manifest["capabilities"]}

    assert "implementation not authorized" in spec.casefold()
    assert statuses["integration.browser_bridge"] == "planned"
    assert statuses["integration.mcp_host"] == "planned"
    for forbidden_production_path in (
        REPO / "skill" / "scripts" / "browser_bridge.py",
        REPO / "skill" / "scripts" / "mcp_server.py",
        REPO / "browser-extension",
    ):
        assert not forbidden_production_path.exists()
