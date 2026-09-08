"""Harness kit templates must stay personal-data-free and parameterized."""
import re
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
HARNESS_ROOT = REPO / "harness" / "skills"
EXPECTED_TEMPLATES = {
    "read-inbox-export",
    "evidence-outreach",
    "learning-capture",
    "catch-up",
}
FORBIDDEN_TOKENS = (
    "C:\\Users",
    "OneDrive",
    "ridi.pillaca",
    "RikepilB",
    "api.normal.fast",
    "251af31ec12848ab9d956c88f11da126",
    "Second Brain",
)
ABSOLUTE_PATH_RE = re.compile(r"[A-Za-z]:\\\\")
FRONTMATTER_NAME_RE = re.compile(r"^name:\s*([A-Za-z0-9-]+)\s*$", re.M)


def _templates() -> dict[str, str]:
    return {
        folder.name: (folder / "SKILL.md").read_text(encoding="utf-8")
        for folder in sorted(HARNESS_ROOT.iterdir())
        if folder.is_dir()
    }


def test_kit_ships_the_expected_template_set():
    assert set(_templates()) == EXPECTED_TEMPLATES


def test_each_template_has_valid_frontmatter_matching_its_folder():
    for name, content in _templates().items():
        assert content.startswith("---\n"), name
        frontmatter = content.split("---\n", 2)[1]
        match = FRONTMATTER_NAME_RE.search(frontmatter)
        assert match and match.group(1) == name
        assert "description:" in frontmatter


def test_templates_carry_no_personal_data_or_machine_paths():
    for name, content in _templates().items():
        for token in FORBIDDEN_TOKENS:
            assert token not in content, f"{name} leaks {token!r}"
        assert not ABSOLUTE_PATH_RE.search(content), f"{name} leaks an absolute path"


def test_inbox_template_is_parameterized_not_hardwired():
    content = _templates()["read-inbox-export"]
    assert "{{VAULT_INBOX}}" in content
    assert "{{SHARED_INBOX}}" in content


def test_outreach_template_requires_evidence_citations():
    content = _templates()["evidence-outreach"]
    for label in ("[MM:SS]", "[image N]", "[message N]"):
        assert label in content
    assert "never the same text twice" in content.casefold()
