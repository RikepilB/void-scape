"""The public skill stays Codex-first and does not name unsupported harness tools."""
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENV_EXAMPLE = REPO / ".env.example"
SKILL_MD = REPO / "skill" / "SKILL.md"
AUTH_GUIDE = REPO / "docs" / "authenticated-sources.md"
ARCHITECTURE = REPO / "docs" / "architecture.md"
WORKFLOW = REPO / "docs" / "workflow.md"
VOIDSCAPE_GUIDE = REPO / "docs" / "voidscape-guide.md"
SUBMISSION = REPO / "docs" / "build-week-submission.md"
PROVENANCE = REPO / "docs" / "BUILD_WEEK_PROVENANCE.md"
CREDITS = REPO / "CREDITS.md"
IMPORT_AUDIT = REPO / "docs" / "read-video-import-audit.md"
LANDING_PAGE = REPO / "docs" / "index.html"
PRIVACY_PAGE = REPO / "docs" / "privacy.html"
TERMS_PAGE = REPO / "docs" / "terms.html"
FAQ_PAGE = REPO / "docs" / "faq.html"
GUIDE_PAGE = REPO / "docs" / "guide.html"


def test_skill_md_is_codex_first():
    content = SKILL_MD.read_text(encoding="utf-8")
    assert "Codex" in content


def test_skill_md_frontmatter_still_present():
    content = SKILL_MD.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    frontmatter_end = content.index("\n---\n", 4)
    frontmatter = content[4:frontmatter_end]
    assert "name:" in frontmatter
    assert "description:" in frontmatter


def test_authenticated_source_guide_keeps_access_layers_explicit():
    content = AUTH_GUIDE.read_text(encoding="utf-8")
    for required in (
        "public media URL",
        "READ_VIDEO_YTDLP_COOKIES",
        "ChatGPT Chrome extension",
        "Chrome-control skill",
        "VPN",
        "not a Voidscape dependency",
    ):
        assert required in content


def test_cookie_exports_are_ignored_regardless_of_prefix():
    content = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert "*cookies*.txt" in content.splitlines()


def test_public_metadata_has_no_legacy_repository_or_competitor_links():
    public_files = (
        REPO / ".github" / "ISSUE_TEMPLATE" / "config.yml",
        REPO / "docs" / "ROADMAP.md",
    )
    combined = "\n".join(path.read_text(encoding="utf-8") for path in public_files).lower()
    legacy_repo = "github.com/rikepilb/" + "read-video"
    competitor = "anth" + "ropic"
    assert legacy_repo not in combined
    assert competitor not in combined


def test_landing_page_uses_voidscape_identity_only():
    content = LANDING_PAGE.read_text(encoding="utf-8").lower()
    legacy_name = "read-" + "video"
    assert legacy_name not in content
    assert "github.com/rikepilb/void-scape" in content
    assert "open voidscape on github" in content


def test_landing_navigation_stays_focused_and_links_legal_pages():
    content = LANDING_PAGE.read_text(encoding="utf-8")
    nav = content.split('<nav aria-label="Primary navigation">', 1)[1].split("</nav>", 1)[0]
    for label in ("Install", "Guide", "FAQ", "GitHub", "Privacy", "Terms"):
        assert f">{label}" in nav or f">{label} " in nav
    for removed in ("Sequence", "Screening", "Workflow"):
        assert f">{removed}<" not in nav
    assert 'href="privacy.html"' in nav
    assert 'href="terms.html"' in nav
    assert 'href="guide.html"' in nav


def test_legal_pages_are_separate_truthful_prototype_drafts():
    privacy = PRIVACY_PAGE.read_text(encoding="utf-8")
    terms = TERMS_PAGE.read_text(encoding="utf-8")
    for page in (privacy, terms):
        assert "DRAFT — not reviewed by counsel." in page
        assert 'href="legal.css"' in page
        assert 'href="index.html#install"' in page
        assert 'href="index.html#faq"' in page
        assert "github.com/RikepilB/void-scape" in page
        assert "https://voidscape.club/" in page
        assert "rikepilb.github.io/void-scape" not in page
    for claim in (
        "sets no Voidscape cookies",
        "runs no analytics",
        "served through Vercel",
        "--allow-cloud",
        "--allow-model-download",
        "Voidscape has no project-operated database",
    ):
        assert claim in privacy
    assert "GitHub Pages" not in privacy
    assert "GitHub Pages" not in terms
    assert "These prototype terms do not remove rights granted by that licence." in terms
    assert "No governing-law or dispute-resolution clause has been selected" in terms


def test_landing_page_has_five_fast_faqs_and_links_to_the_full_faq():
    content = LANDING_PAGE.read_text(encoding="utf-8")
    faq = content.split('<section class="faq" id="faq">', 1)[1].split("</section>", 1)[0]
    assert faq.count("<details>") == 5
    assert 'href="faq.html"' in faq
    assert "Browse all questions" in faq


def test_full_faq_page_is_categorized_and_has_at_least_twenty_answers():
    content = FAQ_PAGE.read_text(encoding="utf-8")
    assert 'href="faq.css"' in content
    assert 'aria-current="page"' in content
    assert content.count("<details>") >= 20
    assert f"{content.count('<details>')} answers" in content
    assert "\u00e2" not in content
    for category in (
        "Getting started",
        "Evidence and results",
        "Privacy and cost",
        "Sources and sign-in",
        "Agents and follow-up work",
        "Troubleshooting and roadmap",
    ):
        assert category in content


def test_website_guide_tells_the_current_workflow_and_labels_planned_work():
    landing = LANDING_PAGE.read_text(encoding="utf-8")
    guide = GUIDE_PAGE.read_text(encoding="utf-8")
    assert 'href="guide.html"' in landing
    assert "Guide: how it works" in landing
    for required in (
        "Inspect",
        "Preview",
        "Read",
        "Available today",
        "Coming soon",
        "not a promise",
        "Transcription is one channel",
        "Already have a transcript?",
    ):
        assert required in guide
    for required in (
        "Transcription is one channel",
        "Agent-native protocol",
        "Scoped visual reads",
        "One inspectable evidence bundle",
    ):
        assert required in landing


def test_architecture_describes_current_cost_timeline_and_backend_contracts():
    content = ARCHITECTURE.read_text(encoding="utf-8")
    for required in (
        "openai_patch32",
        "source timeline",
        "google-genai",
        "fast input seek",
        "does not silently move from a local path to a cloud provider",
    ):
        assert required in content


def test_workflow_names_both_explicit_approval_fields():
    content = WORKFLOW.read_text(encoding="utf-8")
    assert "requires_cloud_approval" in content
    assert "needs_model_download" in content
    assert "--allow-cloud" in content
    assert "--allow-model-download" in content


def test_env_example_names_only_supported_backends_and_does_not_imply_autoload():
    content = ENV_EXAMPLE.read_text(encoding="utf-8")
    assert "does not auto-load .env files" in content
    assert "OPENAI_API_KEY=" in content
    assert "XAI_API_KEY" not in content
    assert "GITHUB_TOKEN" not in content


def test_guide_claims_only_shipped_agent_surface():
    content = VOIDSCAPE_GUIDE.read_text(encoding="utf-8")
    assert "repository's Codex `/voidscape` router" not in content
    assert "Audio-only reads" in content
    assert "installed CLI" in content


def test_submission_records_live_pages_and_published_provenance():
    submission = SUBMISSION.read_text(encoding="utf-8")
    provenance = PROVENANCE.read_text(encoding="utf-8")
    assert "| Public distribution | Present |" in submission
    assert "needs an authorized commit/push" not in submission
    assert "52bc01e" in provenance


def test_credits_distinguish_gemini_sdk_from_compatible_http_backends():
    content = CREDITS.read_text(encoding="utf-8")
    assert "Gemini uses the optional `google-genai` SDK" in content


def test_import_audit_covers_every_distributable_component_and_private_exclusion():
    content = IMPORT_AUDIT.read_text(encoding="utf-8")
    for required in (
        "skill/scripts/video.py",
        "skill/scripts/voidscape.py",
        "compat/read-video/",
        "scripts/install-skill.ps1",
        "scripts/create-demo-fixture.py",
        "scripts/instagram_capture_helper.py",
        "tests/",
        "`.env`",
        "`docs/handoff/`",
        "generated demo videos",
    ):
        assert required in content
