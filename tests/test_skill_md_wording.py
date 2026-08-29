"""The public skill stays Codex-first and does not name unsupported harness tools."""
import json
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
README = REPO / "README.md"
CLI_REFERENCE = REPO / "docs" / "cli-reference.md"
DEMO_SHOT_LIST = REPO / "docs" / "demo-shot-list.md"
HARNESS_SUPPORT = REPO / "docs" / "harness-support.md"
CHROME_MATRIX = REPO / "docs" / "chrome-use-case-matrix.md"
ROADMAP = REPO / "docs" / "ROADMAP.md"
IMAGE_DESIGN = REPO / "docs" / "superpowers" / "specs" / "2026-07-21-image-carousel-reader-design.md"
IMAGE_PLAN = REPO / "docs" / "superpowers" / "plans" / "2026-07-21-image-carousel-reader.md"
BROWSER_BRIDGE_DESIGN = (
    REPO / "docs" / "superpowers" / "specs"
    / "2026-08-28-harness-neutral-browser-bridge-design.md"
)


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


def test_browser_and_remote_docs_keep_host_boundary_explicit():
    readme = README.read_text(encoding="utf-8")
    harness = HARNESS_SUPPORT.read_text(encoding="utf-8")
    auth = AUTH_GUIDE.read_text(encoding="utf-8")
    matrix = CHROME_MATRIX.read_text(encoding="utf-8")

    assert "docs/harness-support.md" in readme
    for required in (
        "ChatGPT Remote",
        "Claude Code Remote Control",
        "host must remain awake",
        "local Voidscape CLI",
        "A model without tool access cannot run Voidscape directly",
    ):
        assert required in harness
    assert "Browser access does not become CLI authentication" in auth
    assert "Vendor-documented" in matrix
    assert "Richard-tested" in matrix


def test_harness_docs_do_not_claim_automatic_universal_support():
    content = HARNESS_SUPPORT.read_text(encoding="utf-8")
    assert "does not mean one extension automatically supports every model and harness" in content
    for required in (
        "transport",
        "tool discovery",
        "permissions",
        "approval",
        "host routing",
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


def test_local_image_and_carousel_reader_is_documented_in_release_candidate_sources():
    skill = SKILL_MD.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    reference = CLI_REFERENCE.read_text(encoding="utf-8")
    guide = VOIDSCAPE_GUIDE.read_text(encoding="utf-8")
    landing = LANDING_PAGE.read_text(encoding="utf-8")
    demo = DEMO_SHOT_LIST.read_text(encoding="utf-8")

    available = landing.split("01 / Available now", 1)[1].split(
        "02 / Coming soon", 1,
    )[0]
    planned = landing.split("02 / Coming soon", 1)[1]
    assert "Image and carousel reading" in available
    assert "Image and carousel reading" not in planned
    for content in (skill, readme, reference, guide):
        assert "image.py manifest --compact" in content
        assert "[image 1]" in content
        assert "non-recursive" in content
        assert "100 images" in content
    assert "must contain exactly one frame" in reference
    assert "Animated APNG and WebP inputs are unsupported" in reference
    assert "45–60 second image/carousel demo" in demo
    assert "slide1.png" in demo
    assert "slide10.png" in demo


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


def test_roadmap_and_image_plan_match_local_release_state():
    roadmap = ROADMAP.read_text(encoding="utf-8")
    design = IMAGE_DESIGN.read_text(encoding="utf-8")
    plan = IMAGE_PLAN.read_text(encoding="utf-8")

    assert "Local images and carousels" in roadmap
    assert "shipped in PR #9" in roadmap
    assert "separate design and security review" in roadmap
    assert "**Status:** Shipped in PR #9 (merged 2026-08-28)" in design
    assert "**Status:** Shipped in PR #9 (merged 2026-08-28)" in plan


def test_image_design_probe_schema_matches_the_stable_implementation_names():
    design = IMAGE_DESIGN.read_text(encoding="utf-8")
    schema_text = design.split("Probe data shape:", 1)[1].split(
        "```json", 1,
    )[1].split("```", 1)[0]
    schema = json.loads(schema_text)

    assert schema["within_limit"] is True
    assert "items" not in schema
    assert set(schema["images"][0]) == {
        "index", "source", "source_name", "width", "height", "bytes",
    }


def test_completed_image_plan_snippets_teach_current_contracts():
    plan = IMAGE_PLAN.read_text(encoding="utf-8")

    for required in (
        "return natural, path.name.casefold(), path.name",
        '"-count_frames"',
        '"nb_read_frames"',
        "expected exactly one frame",
        '"within_limit": len(images) <= MAX_IMAGES',
        'raise ValueError("out_words cannot be negative")',
        "drivers_usd",
        'model_rate["output"]',
        'args.agent_model or _defaults(workspace)["agent_model"]',
    ):
        assert required in plan


def test_browser_bridge_design_exists_and_states_security_boundaries():
    assert BROWSER_BRIDGE_DESIGN.is_file()
    content = BROWSER_BRIDGE_DESIGN.read_text(encoding="utf-8")
    assert "**Status:** Design approved for review" in content
    for required in (
        "dedicated repository",
        "native messaging",
        "loopback",
        "MCP-style tool calls",
        "{ok,data,error,meta}",
        "capability negotiation",
        "host routing",
        "--allow-cloud",
        "--allow-model-download",
        "inspect → preview → read",
        "never reads browser credentials, cookies, storage, or secrets",
        "Richard-tested",
        "Vendor-documented",
        "Unverified",
        "ChatGPT / Codex adapter",
        "Claude adapter",
        "origin validation",
        "local port exposure",
        "command injection",
        "cross-profile access",
        "credential leakage",
    ):
        assert required in content
