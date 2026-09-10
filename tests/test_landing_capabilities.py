"""The public roadmap must distinguish reading from unshipped account automation."""
from pathlib import Path


def test_landing_capability_labels_and_permission_boundaries():
    html = (Path(__file__).resolve().parents[1] / "docs" / "index.html").read_text(encoding="utf-8")
    section = html.split('id="capabilities"', 1)[1].split('<section class="start', 1)[0]
    for label in (
        "01 / Available now", "02 / In progress", "03 / Next", "04 / Later",
        "Easy cron setup is not shipped", "not Watch Later", "Subscription access is not API credit",
        "separate companion directions", "Security review gates still apply",
        "RSS/Atom", "filename-ordered carousels",
    ):
        assert label in section
    assert section.count("<details") == section.count("</details>") == 5
    for number in (2, 3, 4):
        assert f'https://github.com/RikepilB/void-scape/milestone/{number}' in section
    assert "Iris remains STOPPED" in section
    assert "Codex plugin remains DO NOT INSTALL" in section
    assert "static scan warnings are not evidence of malware" in section
    assert "no delivery date is promised" in section


def test_roadmap_has_sequenced_work_and_no_blanket_one_day_promise():
    repo = Path(__file__).resolve().parents[1]
    roadmap = (repo / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
    for number in (1, 2, 3, 4):
        assert f'https://github.com/RikepilB/void-scape/milestone/{number}' in roadmap
    for number in (42, 44, 54, 55, 56, 57, 58, 91, 92, 93, 94, 95, 96):
        assert f'https://github.com/RikepilB/void-scape/issues/{number}' in roadmap
    assert "one-day build plan or a promise of delivery dates" in roadmap
    assert "implementation exists, acceptance remains" in roadmap
    assert "Iris remains **STOPPED**" in roadmap
