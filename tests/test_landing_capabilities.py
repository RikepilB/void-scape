"""The public roadmap must distinguish reading from unshipped account automation."""
from pathlib import Path


def test_landing_capability_labels_and_permission_boundaries():
    html = (Path(__file__).resolve().parents[1] / "docs" / "index.html").read_text(encoding="utf-8")
    section = html.split('id="capabilities"', 1)[1].split('<section class="start', 1)[0]
    for label in (
        "01 / Available now", "02 / Designed next", "03 / Exploration, not promised",
        "Easy cron setup is not shipped", "not Watch Later", "Subscription access is not API credit",
        "separate companion directions", "Security review gates still apply",
        "RSS/Atom", "filename-ordered carousels",
    ):
        assert label in section
    assert section.count("<details") == section.count("</details>") == 4
