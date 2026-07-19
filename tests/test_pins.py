import json
from pathlib import Path

import video
from conftest import requires_ffmpeg


@requires_ffmpeg
def test_pins_appear_in_manifest(scene_clip, tmp_path):
    res = video.run(str(scene_clip), tier="visual", frames=5, workdir=str(tmp_path),
                    timestamps="1,05")
    pinned = [e for e in res["frames"] if e.get("pinned")]
    assert len(pinned) == 2
    assert {e["t"] for e in pinned} == {"00:01", "00:05"}
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert sum(1 for e in manifest["frames"] if e.get("pinned")) == 2


@requires_ffmpeg
def test_bad_and_out_of_range_pins_skipped(scene_clip, tmp_path, capsys):
    res = video.run(str(scene_clip), tier="visual", frames=5, workdir=str(tmp_path),
                    timestamps="abc,99:99:99,2")
    pinned = [e for e in res["frames"] if e.get("pinned")]
    assert len(pinned) == 1                        # only "2" is valid and in range
    err = capsys.readouterr().err
    assert "abc" in err and "skipped" in err


@requires_ffmpeg
def test_pin_overflow_keeps_first_budget_pins(scene_clip, tmp_path, capsys):
    res = video.run(str(scene_clip), tier="visual", frames=2, workdir=str(tmp_path),
                    timestamps="1,2,3,4,5")
    pinned = [e for e in res["frames"] if e.get("pinned")]
    assert len(pinned) == 2
    assert {e["t"] for e in pinned} == {"00:01", "00:02"}
    assert "exceed" in capsys.readouterr().err
