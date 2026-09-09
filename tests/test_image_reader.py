"""Local image and filename-ordered carousel evidence preparation."""
import base64
import json
import subprocess
import sys
from pathlib import Path

import pytest

import image
from conftest import requires_ffmpeg


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUB"
    "AScY42YAAAAASUVORK5CYII="
)
JPEG_16X16 = base64.b64decode(
    "/9j/4AAQSkZJRgABAgAAAQABAAD//gAQTGF2YzYyLjI4LjEwMAD/2wBDAAgEBAQEBAUF"
    "BQUFBQYGBgYGBgYGBgYGBgYHBwcICAgHBwcGBgcHCAgICAkJCQgICAgJCQoKCgwMCwsO"
    "Dg4RERT/xABMAAEBAAAAAAAAAAAAAAAAAAAABgEBAQAAAAAAAAAAAAAAAAAABgcQAQAA"
    "AAAAAAAAAAAAAAAAAAARAQAAAAAAAAAAAAAAAAAAAAD/wAARCAAQABADASIAAhEAAxEA"
    "/9oADAMBAAIRAxEAPwCLAE1/f//Z"
)
WEBP_16X16 = base64.b64decode(
    "UklGRjwAAABXRUJQVlA4IDAAAADQAQCdASoQABAAAgA0JaACdLoB+AADsAD+8Oj3/yC5"
    "YXXI1/8gP+QH/ID/+PIAAAA="
)
ANIMATED_WEBP_16X16 = base64.b64decode(
    "UklGRs4BAABXRUJQVlA4WAoAAAACAAAADwAADwAAQU5JTQYAAAD/////AABBTk1G9AAA"
    "AAAAAAAAAA8AAA8AAPQBAAJWUDgg3AAAADADAJ0BKhAAEAACADQlsAJ0RgBlgHSJj6Pz"
    "JAus2lMurcAA/vlX9qXpLas+vE7GIiHrHzfHrzpee3lX8b7Q7d2wCe7Gv/iG/3vtzq9"
    "yB07+f6nyScMeXeDr/4q19d9kBH4JDmcv8g8HzW/3nGO0yhd3nijpW/+/13avNX3Pl4"
    "TkbCns2Zl98VgnP3mzy/9H/91mdS6F8d5h/5oug2PfcRpOif7Dr38X4Ljb/Svkw/rEu"
    "McBuKXT/hL7yH9RHb5JMMHbIf3af9XRlZP/8jq4RYaY+4unfS3JIj2AAABBTk1GpgAA"
    "AAAAAAAAAAgAAAoAAPQBAABWUDggjgAAABQCAJ0BKgkACwAAADQlsAJ0MFDBRxBwqyAA"
    "/vibwhL0l6YP/dGcSX/06Owf3BaLX28CCKCmZee3q0/M8E/G9r4EqgI4ypGenfO/9vZ"
    "97qUbOHpk08zF/5O5/4+464n4DfoRHU+XvfXM4f9aaVeJSzG/3hPPftv+P5Sz74wa2J"
    "wyz/z5lta/6fW5LgkAAAA="
)
ANIMATED_APNG_16X16 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAACXBIWXMAAAABAAAAAQBP"
    "JcTWAAAACGFjVEwAAAACAAAAAPONk3AAAAAaZmNUTAAAAAAAAAAQAAAAEAAAAAAAAAAA"
    "AAEAAgAAbVWenQAAARhJREFUeJxjrGf4x4ANNCKx/zH8Z2BgYPrPxMDAwMJAImCBUPMZ"
    "HPAosgfbwGDPSIEN9NIgxnCegYFhS4MyAwPDbyaQlHndDQYGBiEGUPjc8pbBYkN7SzvD"
    "nzmVDRc+MjBMbDKZ2DUxvyyfgYGhrqaOgWHe1KnXWOrAuveDVR+oZ2D4nWO/j4HBluH"
    "wYbt1dQz/6pOD6yFGlTBttWNQsKOGpw0/MiQk6P3w0sqvnIEs7vH6UHZ2CDVsOM/PcH"
    "79pcOHBRgY7BgYDsHFd4ja7Vj1ijIbVDcxFBWFrWQ/uGDBS1GGQxObTNZyzM0vyzdlY"
    "KqrqbvlDQ5WNAP6+lYFhoonJIjH/pFlYGCARAIDA0NTS1N3p0x2thYA9+hTdFTKPA0A"
    "AAAaZmNUTAAAAAEAAAAIAAAACgAAAAAAAAAAAAEAAgAAz6iwnwAAAFlmZEFUAAAAAnic"
    "Y/zLgADM/0Dk3/8gkgVJHAWwNDGAlM1ncGBgYJBjAgkpQiRw6qBMQozhPAMDw5YGZSw6"
    "2lvaGf7MqWy4gCJxqv4zw+8chUY7BgY7nHYAACREEq9xiYySAAAAAElFTkSuQmCC"
)
CLI = Path(__file__).resolve().parent.parent / "skill" / "scripts" / "image.py"


def _cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), *map(str, args)],
        capture_output=True, text=True, timeout=60,
    )


def _write_png(path: Path) -> Path:
    path.write_bytes(PNG_1X1)
    return path


def _write_fixture(path: Path, content: bytes) -> Path:
    path.write_bytes(content)
    return path


@pytest.fixture
def carousel(tmp_path):
    folder = tmp_path / "carousel"
    folder.mkdir()
    for name in ("slide10.png", "slide2.png", "slide1.png"):
        _write_png(folder / name)
    return folder


@requires_ffmpeg
def test_probe_orders_directory_naturally(carousel):
    result = image.probe(str(carousel))

    assert result["kind"] == "carousel"
    assert result["item_count"] == 3
    assert [item["source_name"] for item in result["images"]] == [
        "slide1.png", "slide2.png", "slide10.png",
    ]
    assert [item["index"] for item in result["images"]] == [1, 2, 3]
    assert result["within_limit"] is True
    assert set(result) == {
        "source", "input", "kind", "item_count", "within_limit", "images", "skipped",
    }
    assert set(result["images"][0]) == {
        "index", "source", "source_name", "width", "height", "bytes",
    }


def test_natural_key_totally_orders_leading_zero_and_case_variants():
    paths = [
        Path("slide1.png"),
        Path("Slide1.png"),
        Path("slide01.png"),
        Path("SLIDE1.png"),
    ]

    assert [path.name for path in sorted(paths, key=image._natural_key)] == [
        "slide01.png", "SLIDE1.png", "Slide1.png", "slide1.png",
    ]


@requires_ffmpeg
def test_probe_supports_one_image(tmp_path):
    source = _write_png(tmp_path / "cover.PNG")

    result = image.probe(str(source))

    assert result["kind"] == "image"
    assert result["item_count"] == 1
    assert result["images"][0]["width"] == 1
    assert result["images"][0]["height"] == 1
    assert result["skipped"] == []


@requires_ffmpeg
@pytest.mark.parametrize(
    ("suffix", "content"),
    [
        (".jpg", JPEG_16X16),
        (".jpeg", JPEG_16X16),
        (".webp", WEBP_16X16),
    ],
)
def test_probe_accepts_embedded_static_supported_formats(tmp_path, suffix, content):
    source = _write_fixture(tmp_path / f"cover{suffix}", content)

    result = image.probe(str(source))

    assert result["kind"] == "image"
    assert result["item_count"] == 1
    assert result["images"][0]["source_name"] == source.name
    assert result["images"][0]["width"] == 16
    assert result["images"][0]["height"] == 16


@requires_ffmpeg
def test_probe_skips_unsupported_entries_and_symlinks(tmp_path):
    folder = tmp_path / "mixed"
    folder.mkdir()
    _write_png(folder / "1.png")
    (folder / "notes.txt").write_text("not an image", encoding="utf-8")
    nested = folder / "nested"
    nested.mkdir()
    try:
        (folder / "linked.png").symlink_to(folder / "1.png")
    except OSError:
        pass

    result = image.probe(str(folder))

    assert [item["source_name"] for item in result["images"]] == ["1.png"]
    skipped = {item["name"]: item["reason"] for item in result["skipped"]}
    assert skipped["notes.txt"] == "unsupported"
    assert skipped["nested"] == "not a file"
    if (folder / "linked.png").is_symlink():
        assert skipped["linked.png"] == "symlink"


@pytest.mark.parametrize("name", ["photo.gif", "photo.bmp", "photo.heic", "photo.avif"])
def test_recognized_unsupported_extensions_route_to_image_engine(name):
    assert image.is_image_input(name) is True


def test_probe_rejects_unsupported_single_file(tmp_path):
    source = tmp_path / "photo.gif"
    source.write_bytes(b"GIF89a")

    with pytest.raises(ValueError, match="unsupported image format"):
        image.probe(str(source))


def test_probe_rejects_empty_folder(tmp_path):
    with pytest.raises(ValueError, match="no supported images"):
        image.probe(str(tmp_path))


def test_probe_rejects_missing_image_path(tmp_path):
    with pytest.raises(FileNotFoundError, match="no such file or folder"):
        image.probe(str(tmp_path / "missing.png"))


@requires_ffmpeg
@pytest.mark.parametrize(
    ("suffix", "format_name", "content"),
    [
        (".webp", "WebP", ANIMATED_WEBP_16X16),
        (".png", "APNG", ANIMATED_APNG_16X16),
    ],
)
def test_probe_and_envelope_reject_animated_images(
        tmp_path, suffix, format_name, content):
    source = _write_fixture(tmp_path / f"animated{suffix}", content)

    with pytest.raises(
            RuntimeError,
            match=rf"{source.name}.*exactly one frame",
    ):
        image.probe(str(source))

    result = _cli("probe", source, "--envelope", "--compact")
    assert result.returncode == 3, f"{format_name}: {result.stdout}\n{result.stderr}"
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "input_error"
    assert source.name in payload["error"]["message"]


@requires_ffmpeg
def test_estimate_sums_image_tokens_and_needs_no_approval(carousel):
    result = image.estimate(str(carousel), agent_model="gpt-5.6-terra")

    assert result["item_count"] == 3
    assert result["tokens"]["images"] == sum(item["tokens"] for item in result["images"])
    assert result["requires_cloud_approval"] is False
    assert result["needs_model_download"] is False
    assert result["needs_install"] is False
    assert result["free"] is True
    assert result["agent_model"] == "gpt-5.6-terra"


@requires_ffmpeg
def test_estimate_rejects_negative_output_words_directly_and_in_envelope(tmp_path):
    source = _write_png(tmp_path / "cover.png")

    with pytest.raises(ValueError, match="out_words cannot be negative"):
        image.estimate(str(source), out_words=-1)

    result = _cli(
        "estimate", source, "--out-words", "-1", "--envelope", "--compact",
    )
    assert result.returncode == 3
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "input_error"
    assert payload["error"]["exit_code"] == 3


@requires_ffmpeg
def test_estimate_counts_fixed_overhead_as_a_dominant_cost_driver(tmp_path):
    source = _write_png(tmp_path / "cover.png")

    result = image.estimate(str(source), out_words=0)

    assert result["tokens"]["overhead"] == 2000
    assert result["dominant_cost"] == "overhead"


@requires_ffmpeg
def test_estimate_uses_usd_contributions_for_dominant_cost(tmp_path):
    source = _write_png(tmp_path / "cover.png")

    result = image.estimate(str(source), out_words=1000)
    pricing = image.video.load_pricing()
    _, rate, _ = image.video._agent_rate(pricing, result["agent_model"])

    assert result["tokens"]["overhead"] > result["tokens"]["output"]
    assert (
        result["tokens"]["output"] * rate["output"]
        > result["tokens"]["overhead"] * rate["input"]
    )
    assert result["dominant_cost"] == "output"


@requires_ffmpeg
def test_run_copies_ordered_original_bytes_and_writes_manifest(carousel, tmp_path):
    originals = {path.name: path.read_bytes() for path in carousel.iterdir()}
    workdir = tmp_path / "out"

    result = image.run(str(carousel), str(workdir))

    assert [Path(item["file"]).name for item in result["images"]] == [
        "001-slide1.png", "002-slide2.png", "003-slide10.png",
    ]
    assert json.loads((workdir / "manifest.json").read_text(encoding="utf-8")) == result
    assert {path.name: path.read_bytes() for path in carousel.iterdir()} == originals
    for item in result["images"]:
        assert Path(item["file"]).read_bytes() == originals[item["source_name"]]


@requires_ffmpeg
def test_run_rejects_nonempty_workdir_before_copy(carousel, tmp_path):
    workdir = tmp_path / "out"
    workdir.mkdir()
    (workdir / "stale.txt").write_text("stale", encoding="utf-8")

    with pytest.raises(ValueError, match="workdir already exists and is not empty"):
        image.run(str(carousel), str(workdir))

    assert not (workdir / "images").exists()


@requires_ffmpeg
def test_estimate_and_run_reject_more_than_100_images(tmp_path):
    folder = tmp_path / "large"
    folder.mkdir()
    for index in range(101):
        _write_png(folder / f"{index}.png")

    assert image.probe(str(folder))["within_limit"] is False
    with pytest.raises(ValueError, match="more than 100"):
        image.estimate(str(folder))
    with pytest.raises(ValueError, match="more than 100"):
        image.run(str(folder), str(tmp_path / "out"))
    assert not (tmp_path / "out").exists()


@requires_ffmpeg
def test_copy_failure_leaves_no_success_manifest(carousel, tmp_path, monkeypatch):
    def fail_copy(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(image.shutil, "copy2", fail_copy)
    workdir = tmp_path / "out"

    with pytest.raises(RuntimeError, match="copy failed"):
        image.run(str(carousel), str(workdir))

    assert not (workdir / "manifest.json").exists()


@requires_ffmpeg
def test_raw_manifest_and_compact_envelope_contract(carousel):
    manifest = _cli("manifest", "--compact")
    probe = _cli("probe", carousel, "--envelope", "--compact")

    assert manifest.returncode == 0, manifest.stderr
    contract = json.loads(manifest.stdout)
    assert contract["protocol_version"] == "1.0"
    assert set(contract["commands"]) == {"manifest", "probe", "estimate", "run"}
    assert probe.returncode == 0, probe.stderr
    payload = json.loads(probe.stdout)
    assert payload["ok"] is True
    assert payload["data"]["kind"] == "carousel"
    assert payload["meta"] == {"command": "probe", "protocol_version": "1.0", "warnings": []}


def test_raw_cli_errors_have_protocol_exit_codes(tmp_path):
    missing = _cli("probe", tmp_path / "missing.png", "--envelope", "--compact")
    usage = _cli("probe", "--not-a-real-flag", "--envelope", "--compact")

    assert missing.returncode == 3
    assert json.loads(missing.stdout)["error"]["code"] == "input_error"
    assert usage.returncode == 2
    assert json.loads(usage.stdout)["error"]["code"] == "usage_error"


@requires_ffmpeg
def test_corrupt_image_envelope_is_input_error(tmp_path):
    corrupt = tmp_path / "corrupt.png"
    corrupt.write_bytes(b"not an image")

    result = _cli("probe", corrupt, "--envelope", "--compact")

    assert result.returncode == 3
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "input_error"
    assert payload["error"]["exit_code"] == 3


def test_missing_ffprobe_main_envelope_is_dependency_error(tmp_path, monkeypatch, capsys):
    source = _write_png(tmp_path / "cover.png")

    def missing_ffprobe(*_args, **_kwargs):
        raise FileNotFoundError("ffprobe")

    monkeypatch.setattr(image.subprocess, "run", missing_ffprobe)

    assert image.main(["probe", str(source), "--envelope", "--compact"]) == 5
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["code"] == "dependency_error"
    assert payload["error"]["exit_code"] == 5


@requires_ffmpeg
def test_copy_failure_main_envelope_is_operation_error(
        carousel, tmp_path, monkeypatch, capsys):
    def fail_copy(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(image.shutil, "copy2", fail_copy)
    workdir = tmp_path / "out"

    assert image.main([
        "run", str(carousel), "--workdir", str(workdir),
        "--envelope", "--compact",
    ]) == 6
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["code"] == "operation_failed"
    assert payload["error"]["exit_code"] == 6
    assert not (workdir / "manifest.json").exists()
