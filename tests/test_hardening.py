import json
from pathlib import Path

import video


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
    assert video._ytdlp_cookie_args() == []


def test_ytdlp_cookie_args_missing_file_ignored(monkeypatch, tmp_path):
    monkeypatch.setenv("READ_VIDEO_YTDLP_COOKIES", str(tmp_path / "nope.txt"))
    assert video._ytdlp_cookie_args() == []


def test_ytdlp_cookie_args_present_when_file_exists(monkeypatch, tmp_path):
    cookies = tmp_path / "cookies.txt"
    cookies.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    monkeypatch.setenv("READ_VIDEO_YTDLP_COOKIES", str(cookies))
    assert video._ytdlp_cookie_args() == ["--cookies", str(cookies)]


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
    video.ytdlp_meta("https://www.instagram.com/reel/abc123/")
    assert "--cookies" in seen["args"]
    assert str(cookies) in seen["args"]
