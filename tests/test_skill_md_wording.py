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
PUBLIC_HTML_PAGES = tuple(
    REPO / "docs" / name
    for name in ("index.html", "guide.html", "faq.html", "privacy.html", "terms.html")
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
    assert "view source" in content


def test_public_pages_use_the_voidscape_favicon_assets():
    for page in PUBLIC_HTML_PAGES:
        content = page.read_text(encoding="utf-8")
        assert 'rel="icon" type="image/svg+xml" href="favicon.svg"' in content
        assert 'rel="icon" type="image/png" sizes="32x32" href="favicon-32.png"' in content
        assert 'rel="apple-touch-icon" sizes="180x180" href="apple-touch-icon.png"' in content
    for name in ("favicon.svg", "favicon-32.png", "apple-touch-icon.png"):
        assert (REPO / "docs" / name).is_file()


def test_public_pages_show_the_voidscape_logo_and_theme_control():
    for page in PUBLIC_HTML_PAGES:
        content = page.read_text(encoding="utf-8")
        assert '<img src="favicon.svg" alt="" width="28" height="28">Voidscape' in content
        assert 'src="site-theme.js"' in content
        assert 'href="site-theme.css"' in content
        assert "data-site-theme-toggle" in content

    theme_script = (REPO / "docs" / "site-theme.js").read_text(encoding="utf-8")
    for forbidden in ("localStorage", "sessionStorage", "document.cookie"):
        assert forbidden not in theme_script
    assert 'backToTop.className = "back-to-top"' in theme_script
    assert "window.scrollY > 700" in theme_script
    assert "window.scrollTo({ top: 0" in theme_script

    theme_styles = (REPO / "docs" / "site-theme.css").read_text(encoding="utf-8")
    assert 'html[data-theme="light"]' in theme_styles
    assert 'html[data-theme="dark"]' in theme_styles
    assert "prefers-reduced-motion" in theme_styles
    assert ".site-header-shell" in theme_styles and "position: sticky" in theme_styles
    assert ".back-to-top.visible" in theme_styles


def test_landing_presents_shipped_readers_as_a_compact_use_case_reel():
    content = LANDING_PAGE.read_text(encoding="utf-8")
    assert content.count("data-carousel-slide") == 6
    assert content.count("data-carousel-dot") == 6
    assert "Images + carousels" in content
    assert "Articles + feeds" in content
    assert "[article N] · [entry N]" in content
    assert 'src="landing.js"' in content

    script = (REPO / "docs" / "landing.js").read_text(encoding="utf-8")
    assert "setInterval" in script
    assert "prefers-reduced-motion" in script
    assert 'mode.textContent = "Manual"' in script
    assert "slide.hidden = !active" in script


def test_landing_manual_carousel_selection_permanently_stops_autoplay():
    script = (REPO / "docs" / "landing.js").read_text(encoding="utf-8")

    assert "if (manuallyStopped || timer || document.hidden) return;" in script
    assert "manuallyStopped = true;" in script

    dot_handler = script.index('dots.forEach((dot, index) => dot.addEventListener("click"')
    stop_call = script.index("stop();", dot_handler)
    selected_slide = script.index("show(index, true);", dot_handler)
    assert stop_call < selected_slide


def test_landing_navigation_stays_focused_and_links_legal_pages():
    content = LANDING_PAGE.read_text(encoding="utf-8")
    nav = content.split('<nav aria-label="Primary navigation">', 1)[1].split("</nav>", 1)[0]
    for label in ("Download", "Guide", "FAQ", "GitHub", "Privacy", "Terms"):
        assert f">{label}" in nav or f">{label} " in nav
    for removed in ("Sequence", "Screening", "Workflow"):
        assert f">{removed}<" not in nav
    assert 'href="privacy.html"' in nav
    assert 'href="terms.html"' in nav
    assert 'href="guide.html"' in nav
    assert 'class="download-link" href="#install"' in nav


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


def test_landing_page_has_three_conversion_faqs_and_links_to_the_full_faq():
    content = LANDING_PAGE.read_text(encoding="utf-8")
    faq = content.split('<section class="faq" id="faq">', 1)[1].split("</section>", 1)[0]
    assert faq.count("<details>") == 3
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


def test_guide_command_examples_scroll_inside_the_mobile_shell():
    content = (REPO / "docs" / "faq.css").read_text(encoding="utf-8")
    assert ".faq-category pre" in content
    assert "max-width: 100%" in content
    assert "overflow-x: auto" in content


def test_website_guide_tells_the_current_workflow_and_labels_capability_boundaries():
    landing = LANDING_PAGE.read_text(encoding="utf-8")
    guide = GUIDE_PAGE.read_text(encoding="utf-8")
    assert 'href="guide.html"' in landing
    assert 'href="guide.html#install"' in landing
    assert "How it works" in landing
    for required in (
        "Inspect",
        "Preview",
        "Read",
        "Available today",
        "Repository-only tools",
        "Articles, RSS, and saved posts",
        "not a promise",
        "Transcription is one channel",
        "Already have a transcript?",
        "winget install --id=astral-sh.uv -e",
        "uv tool install https://github.com/RikepilB/void-scape/archive/refs/heads/main.zip",
        "voidscape init",
    ):
        assert required in guide
    assert "Five commands. The sequence stays the same." in guide
    for command in ("inspect", "preview", "read", "doctor", "customize"):
        assert f"<code>{command}</code>" in guide
    assert 'id="commands"' not in landing
    assert 'id="capabilities"' not in landing
    assert "01 / Available now" not in landing


def test_beginner_install_path_needs_no_clone_and_reaches_grounded_proof():
    landing = LANDING_PAGE.read_text(encoding="utf-8")
    guide = GUIDE_PAGE.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    combined = "\n".join((landing, guide, readme))

    assert "Install once. Use it anywhere." in landing
    for required in (
        "winget install --id=astral-sh.uv -e",
        "curl -LsSf https://astral.sh/uv/install.sh | sh",
        "uv tool install https://github.com/RikepilB/void-scape/archive/refs/heads/main.zip",
        "uv tool update-shell",
        "voidscape init",
        "voidscape customize",
        "voidscape doctor",
        'voidscape inspect "meeting.mp4"',
        'voidscape preview "meeting.mp4"',
        'voidscape read "meeting.mp4" --workdir voidscape-output',
        "voidscape-output/manifest.json",
        "transcript.txt",
        "frames/",
        "[MM:SS]",
        "If the evidence is insufficient, say so.",
    ):
        assert required in combined
    assert "No account, API key, or paid backend is required." in landing
    for content in (landing, guide, readme):
        assert "git clone https://github.com/RikepilB/void-scape.git" not in content
        assert ".\\scripts\\install-skill.ps1" not in content
        assert "bash scripts/install-skill.sh" not in content


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

    assert "Images + carousels" in landing
    assert "Read a slide deck in its real order." in landing
    assert "Evidence: [image 1]" in landing
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
