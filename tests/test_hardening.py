import json
from pathlib import Path
import socket

import pytest

import video


def _resolver(*addresses):
    def resolve(_host, port, *, type):
        assert type == socket.SOCK_STREAM
        return [
            (socket.AF_INET6 if ":" in address else socket.AF_INET, type, 6, "", (address, port))
            for address in addresses
        ]

    return resolve


def test_is_url_accepts_http_https():
    assert video.is_url("https://youtube.com/watch?v=x")
    assert video.is_url("HTTP://example.com/a.mp4")


def test_is_url_rejects_non_urls():
    assert not video.is_url("-malicious.mp4")
    assert not video.is_url("file.mp4")
    assert not video.is_url("ftp://host/x")
    assert not video.is_url("")


def test_ffprobe_local_resolves_path(monkeypatch, tmp_path):
    """The path handed to ffprobe must be absolute even when the caller passes a relative one."""
    seen = {}

    def fake_run_cmd(args):
        seen["args"] = args

        class CP:
            returncode = 0
            stdout = json.dumps({"format": {"duration": "1.0"}, "streams": []})
            stderr = ""
        return CP()

    monkeypatch.setattr(video, "run_cmd", fake_run_cmd)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "-rel.mp4").write_bytes(b"x")
    video.ffprobe_local("-rel.mp4")
    probed = seen["args"][-1]
    assert Path(probed).is_absolute()
    assert not probed.startswith("-")


def test_to_audio_resolves_src(monkeypatch, tmp_path):
    seen = {}

    def fake_run_cmd(args):
        seen["args"] = args
        # satisfy the exists/size check after "encoding"
        Path(args[-1]).write_bytes(b"mp3")

        class CP:
            returncode = 0
            stdout = ""
            stderr = ""
        return CP()

    monkeypatch.setattr(video, "run_cmd", fake_run_cmd)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "-src.mp4").write_bytes(b"x")
    video._to_audio("-src.mp4", tmp_path)
    i = seen["args"].index("-i")
    src_arg = seen["args"][i + 1]
    assert Path(src_arg).is_absolute()
    assert not src_arg.startswith("-")


def test_ytdlp_cookie_args_absent_by_default(monkeypatch):
    monkeypatch.delenv("READ_VIDEO_YTDLP_COOKIES", raising=False)
    assert video._ytdlp_cookie_args("https://example.com/watch") == []


def test_ytdlp_cookie_args_missing_file_ignored(monkeypatch, tmp_path):
    monkeypatch.setenv("READ_VIDEO_YTDLP_COOKIES", str(tmp_path / "nope.txt"))
    assert video._ytdlp_cookie_args("https://example.com/watch") == []


def test_ytdlp_cookie_args_present_when_file_exists(monkeypatch, tmp_path):
    cookies = tmp_path / "cookies.txt"
    cookies.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    monkeypatch.setenv("READ_VIDEO_YTDLP_COOKIES", str(cookies))
    assert video._ytdlp_cookie_args("https://example.com/watch") == ["--cookies", str(cookies)]


def test_ytdlp_meta_passes_cookie_args(monkeypatch, tmp_path):
    cookies = tmp_path / "cookies.txt"
    cookies.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    monkeypatch.setenv("READ_VIDEO_YTDLP_COOKIES", str(cookies))
    seen = {}

    def fake_run_cmd(args):
        seen["args"] = args

        class CP:
            returncode = 0
            stdout = json.dumps({"duration": 1.0})
            stderr = ""
        return CP()

    monkeypatch.setattr(video, "run_cmd", fake_run_cmd)
    monkeypatch.setattr(video, "validate_remote_media_url", lambda url: url)
    video.ytdlp_meta("https://www.instagram.com/reel/abc123/")
    assert "--cookies" in seen["args"]
    assert str(cookies) in seen["args"]


def test_ytdlp_meta_reports_real_error_after_dependency_warning(monkeypatch):
    def fake_run_cmd(_args):
        class CP:
            returncode = 1
            stdout = ""
            stderr = (
                "requests/__init__.py: RequestsDependencyWarning: dependency mismatch\n"
                "  warnings.warn(\n"
                "ERROR: [Instagram] media needs authentication; use --cookies FILE"
            )
        return CP()

    monkeypatch.setattr(video, "run_cmd", fake_run_cmd)
    monkeypatch.setattr(video, "validate_remote_media_url", lambda url: url)

    with pytest.raises(RuntimeError) as exc_info:
        video.ytdlp_meta("https://www.instagram.com/reel/example/")

    message = str(exc_info.value)
    assert "media needs authentication" in message
    assert "RequestsDependencyWarning" not in message


def test_ytdlp_error_redacts_private_urls():
    rendered = video._ytdlp_error(
        "ERROR: failed https://user:secret@example.com/watch?token=private-id#fragment"
    )

    assert "[REDACTED_URL]" in rendered
    assert "secret" not in rendered
    assert "private-id" not in rendered


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "https://user:secret@example.com/video",
        "https://example.com:8080/video",
        "http://example.com:443/video",
    ],
)
def test_remote_media_url_rejects_unsafe_shapes(url):
    with pytest.raises(ValueError, match="remote media URL"):
        video.validate_remote_media_url(url, resolver=_resolver("93.184.216.34"))


@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "fe80::1"])
def test_remote_media_url_rejects_non_public_addresses(address):
    with pytest.raises(ValueError, match="non-public network address"):
        video.validate_remote_media_url(
            "https://example.com/video",
            resolver=_resolver(address),
        )


def test_remote_media_url_requires_every_address_public_and_strips_fragment():
    with pytest.raises(ValueError, match="non-public network address"):
        video.validate_remote_media_url(
            "https://example.com/video",
            resolver=_resolver("93.184.216.34", "127.0.0.1"),
        )
    assert video.validate_remote_media_url(
        "https://example.com/video#fragment",
        resolver=_resolver("93.184.216.34"),
    ) == "https://example.com/video"


def test_remote_media_probe_redacts_query_from_machine_output(monkeypatch):
    monkeypatch.setattr(video, "validate_remote_media_url", lambda url: url)
    monkeypatch.setattr(
        video,
        "run_cmd",
        lambda _args: type(
            "Completed",
            (),
            {"returncode": 0, "stdout": json.dumps({"duration": 1}), "stderr": ""},
        )(),
    )

    result = video.probe("https://example.com/watch?private_token=value#fragment")

    assert result["input"] == "https://example.com/watch"
    assert result["input_redacted"] is True
    assert "private_token" not in json.dumps(result)
