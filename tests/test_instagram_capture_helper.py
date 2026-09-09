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
    main,
    preview,
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


@pytest.mark.parametrize('url', [
    'https://www.instagram.com:private-value/reel/Cx1AbC2DeFg/',
    'https://[broken/reel/Cx1AbC2DeFg/',
])
def test_direct_parser_failures_are_normalized(url):
    with pytest.raises(ValueError) as error:
        extract_shortcode(url)
    assert str(error.value) == 'not a recognizable Instagram reel/post URL or shortcode'
    assert error.value.__suppress_context__ is True


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


@pytest.mark.parametrize("command", ["inspect", "preview"])
def test_read_only_commands_do_not_create_queue(tmp_path, command):
    queue = tmp_path / "absent" / "urls.md"
    args = [sys.executable, str(HELPER_SCRIPT), command,
            "https://www.instagram.com/p/Cx1AbC2DeFg/?igsh=tracking"]
    if command == "preview":
        args.append(str(queue))
    result = subprocess.run(args, capture_output=True, text=True)
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["url"] == canonical_url("Cx1AbC2DeFg")
    assert payload["shortcode"] == "Cx1AbC2DeFg"
    assert payload["mutates_urls_md"] is False
    assert payload["mutates_source"] is False
    assert list(tmp_path.iterdir()) == []
    if command == "preview":
        assert payload["action"] == "append"


def test_preview_duplicate_preserves_exact_bytes(tmp_path):
    queue = tmp_path / "urls.md"
    original = (canonical_url("Cx1AbC2DeFg") + "\r\n# retained comment\r\n").encode()
    queue.write_bytes(original)
    result = preview("Cx1AbC2DeFg", queue)
    assert result["duplicate"] is True
    assert result["action"] == "skip_duplicate"
    assert queue.read_bytes() == original


@pytest.mark.parametrize("url", [
    "https://www.instagram.com/reel/Cx1AbC2DeFg/extra",
    "https://www.instagram.com/reel/abcdefghijklmnop/",
    "https://user:secret@www.instagram.com/reel/Cx1AbC2DeFg/",
    "https://www.instagram.com:443/reel/Cx1AbC2DeFg/",
    "https://www.instagram.com:invalid/reel/Cx1AbC2DeFg/",
    "ftp://www.instagram.com/reel/Cx1AbC2DeFg/",
    "https://www.insta\ngram.com/reel/Cx1AbC2DeFg/",
    "Cx1AbC2DeFg\x00",
])
def test_invalid_identity_fails_without_echo_or_write(tmp_path, capsys, url):
    queue = tmp_path / "urls.md"
    assert main(["process", url, str(queue)]) == 1
    output = capsys.readouterr()
    assert json.loads(output.out) == {
        "error": "Instagram capture validation or queue operation failed"}
    assert output.err == ""
    assert not queue.exists()


def test_queue_confirmation_error_is_sanitized(tmp_path, monkeypatch, capsys):
    import instagram_capture_helper as helper
    from capture_adapter import CapturePartialWriteError

    def fail(*args):
        raise CapturePartialWriteError("private path or token")

    monkeypatch.setattr(helper, "queue_append_result", fail)
    assert main(["process", "Cx1AbC2DeFg", str(tmp_path / "urls.md")]) == 1
    output = capsys.readouterr()
    assert "private" not in output.out + output.err
    assert "error" in json.loads(output.out)
