"""IG follow audit: read-only diff, citable report, no account mutation."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

import ig_follow_audit_helper as audit


REPO = Path(__file__).resolve().parent.parent
HELPER = REPO / "scripts" / "ig_follow_audit_helper.py"

FOLLOWERS_JSON = json.dumps([
    {"href": "https://example.com", "value": "mutualone", "timestamp": 1700000000},
    {"value": "@MutualOne"},          # duplicate after normalization
    {"value": "fan.of.you"},
    {"value": "another.fan"},
])
FOLLOWING_TXT = "mutualone\nbrand.news\nmeme.account\nfan.of.you\n"


@pytest.fixture
def exports(tmp_path):
    followers = tmp_path / "followers.json"
    following = tmp_path / "following.txt"
    followers.write_text(FOLLOWERS_JSON, encoding="utf-8")
    following.write_text(FOLLOWING_TXT, encoding="utf-8")
    return followers, following


def test_load_handles_accepts_json_export_and_plain_list(exports):
    followers, following = exports
    assert audit.load_handles(followers) == ["mutualone", "fan.of.you", "another.fan"]
    assert audit.load_handles(following) == ["mutualone", "brand.news", "meme.account", "fan.of.you"]


def test_diff_categories_are_exclusive_and_cited(exports):
    _, following = exports
    diff = audit.diff_relationships(
        ["mutualone", "fan.of.you", "another.fan"], audit.load_handles(following),
    )
    assert diff["mutual"] == ["fan.of.you", "mutualone"]
    assert diff["not_following_back"] == ["brand.news", "meme.account"]
    assert diff["you_dont_follow_back"] == ["another.fan"]
    assert diff["counts"]["not_following_back"] == 2


def test_preview_reports_plan_without_mutation(exports):
    followers, following = exports
    plan = audit.preview(followers, following)
    assert plan["action"] == "write_local_report"
    assert plan["mutates_source"] is False
    assert plan["never_unfollows"] is True
    assert plan["suggested_review_list"] == "not_following_back"
    assert plan["counts"]["followers"] == 3
    assert plan["counts"]["following"] == 4


def test_process_writes_report_with_user_citations(exports, tmp_path):
    followers, following = exports
    report_dir = tmp_path / "audit-report"
    result = audit.process(followers, following, report_dir)
    report = Path(result["report"]).read_text(encoding="utf-8")
    assert "## Suggested review (not following you back)" in report
    assert "brand.news — [user 1]" in report
    assert "never_unfollows" in json.loads((report_dir / "report.json").read_text(encoding="utf-8"))
    assert result["citation_guide"].startswith("cite each suggested handle with user N")
    assert result["mutates_source"] is False


def test_process_refuses_non_empty_report_dir(exports, tmp_path):
    followers, following = exports
    busy = tmp_path / "busy"
    busy.mkdir()
    (busy / "old.md").write_text("x", encoding="utf-8")
    with pytest.raises(audit.CaptureError, match="not empty"):
        audit.process(followers, following, busy)


def test_missing_export_emits_capture_error(tmp_path):
    result = subprocess.run(
        [sys.executable, str(HELPER), "inspect",
         "--followers", str(tmp_path / "missing.json"),
         "--following", str(tmp_path / "also-missing.json")],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["error_type"] == "capture_error"
    assert "not found" in payload["error"]
