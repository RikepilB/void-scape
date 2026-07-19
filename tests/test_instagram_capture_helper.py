"""Tests for the Instagram capture helper — pure logic only, no browser/network."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from instagram_capture_helper import (
    append_and_confirm,
    canonical_url,
    extract_shortcode,
    is_duplicate,
    process,
)

REPO = Path(__file__).resolve().parent.parent
HELPER_SCRIPT = REPO / "scripts" / "instagram_capture_helper.py"


def test_extract_shortcode_from_reel_url():
    assert extract_shortcode("https://www.instagram.com/reel/Cx1AbC2DeFg/") == "Cx1AbC2DeFg"


def test_extract_shortcode_from_reel_url_with_query_params():
    url = "https://www.instagram.com/reel/Cx1AbC2DeFg/?igsh=abc123"
    assert extract_shortcode(url) == "Cx1AbC2DeFg"


def test_extract_shortcode_from_post_url():
    assert extract_shortcode("https://www.instagram.com/p/Cx1AbC2DeFg/") == "Cx1AbC2DeFg"


def test_extract_shortcode_from_bare_shortcode():
    assert extract_shortcode("Cx1AbC2DeFg") == "Cx1AbC2DeFg"


def test_extract_shortcode_invalid_raises():
    with pytest.raises(ValueError):
        extract_shortcode("https://example.com/not-instagram")


def test_extract_shortcode_rejects_lookalike_domain_no_separator():
    with pytest.raises(ValueError):
        extract_shortcode("https://notinstagram.com/reel/Cx1AbC2DeFg/")
    with pytest.raises(ValueError):
        extract_shortcode("https://xxxinstagram.com/reel/Cx1AbC2DeFg/")


def test_extract_shortcode_rejects_lookalike_domain_with_hyphen_or_underscore():
    with pytest.raises(ValueError):
        extract_shortcode("https://fake-instagram.com/reel/Cx1AbC2DeFg/")
    with pytest.raises(ValueError):
        extract_shortcode("https://fake_instagram.com/reel/Cx1AbC2DeFg/")
    with pytest.raises(ValueError):
        extract_shortcode("https://verify-instagram.com/reel/Cx1AbC2DeFg/")


def test_extract_shortcode_rejects_userinfo_host_spoofing():
    with pytest.raises(ValueError):
        extract_shortcode("https://instagram.com@evil.com/reel/Cx1AbC2DeFg/")


def test_extract_shortcode_from_reel_url_without_www():
    assert extract_shortcode("https://instagram.com/reel/Cx1AbC2DeFg/") == "Cx1AbC2DeFg"


def test_canonical_url_format():
    assert canonical_url("Cx1AbC2DeFg") == "https://www.instagram.com/reel/Cx1AbC2DeFg/"


def test_is_duplicate_true_when_present(tmp_path):
    urls_md = tmp_path / "urls.md"
    urls_md.write_text("https://www.instagram.com/reel/Cx1AbC2DeFg/\n", encoding="utf-8")
    assert is_duplicate("https://www.instagram.com/reel/Cx1AbC2DeFg/", urls_md) is True


def test_is_duplicate_false_when_absent(tmp_path):
    urls_md = tmp_path / "urls.md"
    urls_md.write_text("https://www.instagram.com/reel/Other0000Ab/\n", encoding="utf-8")
    assert is_duplicate("https://www.instagram.com/reel/Cx1AbC2DeFg/", urls_md) is False


def test_is_duplicate_false_when_file_missing(tmp_path):
    urls_md = tmp_path / "does_not_exist.md"
    assert is_duplicate("https://www.instagram.com/reel/Cx1AbC2DeFg/", urls_md) is False


def test_append_and_confirm_creates_file_and_parent_dirs(tmp_path):
    urls_md = tmp_path / "nested" / "urls.md"
    ok = append_and_confirm("https://www.instagram.com/reel/Cx1AbC2DeFg/", urls_md)
    assert ok is True
    assert "https://www.instagram.com/reel/Cx1AbC2DeFg/" in urls_md.read_text(encoding="utf-8")


def test_append_and_confirm_appends_without_truncating_existing(tmp_path):
    urls_md = tmp_path / "urls.md"
    urls_md.write_text("https://www.instagram.com/reel/Existing0001/\n", encoding="utf-8")
    append_and_confirm("https://www.instagram.com/reel/Cx1AbC2DeFg/", urls_md)
    content = urls_md.read_text(encoding="utf-8")
    assert "Existing0001" in content
    assert "Cx1AbC2DeFg" in content


def test_process_new_url_appends(tmp_path):
    urls_md = tmp_path / "urls.md"
    result = process("Cx1AbC2DeFg", urls_md)
    assert result == {
        "url": "https://www.instagram.com/reel/Cx1AbC2DeFg/",
        "duplicate": False,
        "appended": True,
        "safe_to_unsave": True,
    }


def test_process_duplicate_url_skips_append_but_safe_to_unsave(tmp_path):
    urls_md = tmp_path / "urls.md"
    urls_md.write_text("https://www.instagram.com/reel/Cx1AbC2DeFg/\n", encoding="utf-8")
    result = process("Cx1AbC2DeFg", urls_md)
    assert result == {
        "url": "https://www.instagram.com/reel/Cx1AbC2DeFg/",
        "duplicate": True,
        "appended": False,
        "safe_to_unsave": True,
    }


def test_process_invalid_input_raises(tmp_path):
    urls_md = tmp_path / "urls.md"
    with pytest.raises(ValueError):
        process("https://example.com/not-instagram", urls_md)


def test_cli_process_prints_json_for_new_url(tmp_path):
    urls_md = tmp_path / "urls.md"
    result = subprocess.run(
        [sys.executable, str(HELPER_SCRIPT), "process", "Cx1AbC2DeFg", str(urls_md)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["appended"] is True
    assert payload["url"] == "https://www.instagram.com/reel/Cx1AbC2DeFg/"


def test_cli_process_errors_on_invalid_input(tmp_path):
    urls_md = tmp_path / "urls.md"
    result = subprocess.run(
        [sys.executable, str(HELPER_SCRIPT), "process", "https://example.com/nope", str(urls_md)],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert "error" in payload
