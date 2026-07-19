import subprocess
from pathlib import Path

import pytest

import video
from conftest import requires_ffmpeg


def make_jpegs(tmp_path: Path, colors: list[str]) -> list[Path]:
    out = []
    for i, c in enumerate(colors, start=1):
        fp = tmp_path / f"frame_{i:04d}.jpg"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                        "-f", "lavfi", "-i", f"color=c={c}:s=64x64:d=0.1",
                        "-frames:v", "1", str(fp)], check=True, capture_output=True)
        out.append(fp)
    return out


@requires_ffmpeg
def test_thumbs_one_per_frame(tmp_path):
    paths = make_jpegs(tmp_path, ["black", "black", "white"])
    thumbs = video._thumb_frames(paths)
    assert len(thumbs) == 3
    assert all(len(t) == video._DEDUP_THUMB * video._DEDUP_THUMB for t in thumbs)
    assert video._frame_delta(thumbs[0], thumbs[1]) <= video._DEDUP_THRESHOLD
    assert video._frame_delta(thumbs[1], thumbs[2]) > video._DEDUP_THRESHOLD


@requires_ffmpeg
def test_thumbs_fail_open_on_bad_name(tmp_path):
    fp = tmp_path / "noindex.jpg"
    fp.write_bytes(b"not a jpeg")
    assert video._thumb_frames([fp]) == []


def test_thumbs_empty_input():
    assert video._thumb_frames([]) == []
