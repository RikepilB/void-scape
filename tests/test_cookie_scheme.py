"""The user's exported cookie jar never travels over plaintext.

yt-dlp uses `http.cookiejar`, which only restricts cookies carrying the `Secure` attribute. A
non-Secure cookie in an exported jar would otherwise be sent on an `http://` URL in the clear.
"""
import inspect

import pytest

import video


@pytest.fixture
def cookie_jar(tmp_path, monkeypatch):
    jar = tmp_path / "cookies.txt"
    jar.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    monkeypatch.setenv("READ_VIDEO_YTDLP_COOKIES", str(jar))
    return jar


def test_cookies_are_attached_for_https(cookie_jar):
    assert video._ytdlp_cookie_args("https://example.com/watch") == ["--cookies", str(cookie_jar)]


def test_uppercase_https_still_attaches(cookie_jar):
    assert video._ytdlp_cookie_args("HTTPS://example.com/watch") == ["--cookies", str(cookie_jar)]


@pytest.mark.parametrize("url", [
    "http://example.com/watch",
    "HTTP://example.com/watch",
    "ftp://example.com/watch",
    "file:///tmp/local.mp4",
    "example.com/watch",          # no scheme at all
])
def test_cookies_are_withheld_for_anything_but_https(url, cookie_jar):
    assert video._ytdlp_cookie_args(url) == []


def test_no_cookies_configured_attaches_nothing(monkeypatch):
    monkeypatch.delenv("READ_VIDEO_YTDLP_COOKIES", raising=False)
    assert video._ytdlp_cookie_args("https://example.com/watch") == []


def test_a_configured_path_that_does_not_exist_attaches_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("READ_VIDEO_YTDLP_COOKIES", str(tmp_path / "absent.txt"))
    assert video._ytdlp_cookie_args("https://example.com/watch") == []


def test_every_ytdlp_call_site_passes_a_url():
    """The helper is scheme-aware, so no caller may invoke it without the target URL."""
    source = inspect.getsource(video)
    assert "_ytdlp_cookie_args()" not in source, "a call site still omits the URL"
    assert source.count("_ytdlp_cookie_args(url)") == 3
