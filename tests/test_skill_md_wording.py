"""The public skill stays Codex-first and does not name unsupported harness tools."""
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL_MD = REPO / "skill" / "SKILL.md"


def test_skill_md_is_codex_first():
    content = SKILL_MD.read_text(encoding="utf-8")
    assert "Codex" in content
    assert "claude" not in content.lower()


def test_skill_md_frontmatter_still_present():
    content = SKILL_MD.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    frontmatter_end = content.index("\n---\n", 4)
    frontmatter = content[4:frontmatter_end]
    assert "name:" in frontmatter
    assert "description:" in frontmatter
