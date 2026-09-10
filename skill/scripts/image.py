"""Local image and filename-ordered carousel evidence engine."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from datetime import datetime
from urllib.parse import urlsplit

if __package__:
    from . import video
else:
    import video


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
REJECTED_EXTENSIONS = {".gif", ".bmp", ".tif", ".tiff", ".heic", ".heif", ".avif"}
MAX_IMAGES = 100
MAX_PROVENANCE_BYTES = 16384


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _capture_provenance(path: Path, width: int, height: int) -> dict[str, Any]:
    """Validate local claims, never follow paths or URLs supplied by a producer."""
    verified = {"sha256": _sha256(path), "pixel_width": width, "pixel_height": height}
    result = {"status": "missing", "content_trust": "untrusted",
              "coverage": "unknown", "importer_verified": verified,
              "producer_claims": None}
    sidecar = path.with_name(path.name + ".capture.json")
    if sidecar.is_symlink():
        raise ValueError("capture sidecar cannot be a symlink")
    if not sidecar.exists():
        return result
    if not sidecar.is_file():
        raise ValueError("capture sidecar must be a regular file")
    with sidecar.open("rb") as stream:
        raw = stream.read(MAX_PROVENANCE_BYTES + 1)
    if len(raw) > MAX_PROVENANCE_BYTES:
        raise ValueError("capture sidecar exceeds 16384 bytes")
    def invalid():
        # Never echo untrusted values: metadata can contain credentials.
        raise ValueError("invalid capture sidecar schema or geometry")
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                invalid()
            obj[key] = value
        return obj
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=unique)
    except (ValueError, UnicodeError, RecursionError):
        invalid()
    required = {"version", "image_sha256", "producer", "observed_at", "source_url",
                "final_url", "viewport", "pixels", "scale", "mode", "region",
                "readiness_warnings", "content_trust", "derived_from"}
    if not isinstance(data, dict) or set(data) != required:
        invalid()
    if type(data["version"]) is not int or data["version"] != 1:
        raise ValueError("unsupported capture sidecar version")
    if data["content_trust"] != "untrusted":
        invalid()
    def dimensions(obj):
        if not isinstance(obj, dict) or set(obj) != {"width", "height"}:
            invalid()
        if any(type(n) is not int or not 1 <= n <= 1000000 for n in obj.values()):
            invalid()
    def sha(value):
        if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value):
            invalid()
    sha(data["image_sha256"])
    if data["image_sha256"] != verified["sha256"]:
        raise ValueError("capture sidecar image hash mismatch")
    dimensions(data["pixels"])
    if data["pixels"] != {"width": width, "height": height}:
        raise ValueError("capture sidecar image dimensions mismatch")
    if data["viewport"] is not None:
        dimensions(data["viewport"])
    scale = data["scale"]
    if type(scale) not in (int, float) or not 0 < scale <= 16 or not math.isfinite(scale):
        invalid()
    producer = data["producer"]
    if not isinstance(producer, dict) or set(producer) != {"name", "version"}:
        invalid()
    if any(not isinstance(v, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", v)
           for v in producer.values()):
        invalid()
    observed = data["observed_at"]
    if observed is not None:
        try:
            if not isinstance(observed, str) or len(observed) > 40:
                invalid()
            if datetime.fromisoformat(observed.replace("Z", "+00:00")).tzinfo is None:
                invalid()
        except ValueError:
            invalid()
    for key in ("source_url", "final_url"):
        value = data[key]
        if value is not None:
            try:
                if not isinstance(value, str) or len(value) > 4096:
                    invalid()
                parsed = urlsplit(value)
                if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                    invalid()
                port = parsed.port
                host = parsed.hostname.encode("idna").decode("ascii")
                if not re.fullmatch(r"[a-zA-Z0-9.:-]+", host):
                    invalid()
                host = f"[{host}]" if ":" in host else host
                # Paths can carry tokens too. Retain only the origin, never userinfo,
                # paths, query strings or fragments; do not fetch even that origin.
                data[key] = f"{parsed.scheme}://{host}" + (f":{port}" if port else "")
            except (ValueError, UnicodeError):
                invalid()
    warnings = data["readiness_warnings"]
    allowed_warnings = {"unknown", "fonts_pending", "images_pending", "animation_active",
                        "timeout", "partial_capture", "occluded"}
    if not isinstance(warnings, list) or len(warnings) > 7 or any(
            not isinstance(v, str) or v not in allowed_warnings for v in warnings):
        invalid()
    if data["mode"] not in ("viewport", "full_page", "region", "crop", "unknown"):
        invalid()
    parent = data["derived_from"]
    if parent is not None:
        if not isinstance(parent, dict) or set(parent) != {"sha256", "pixels"}:
            invalid()
        sha(parent["sha256"])
        dimensions(parent["pixels"])
    if (data["mode"] == "crop") != (parent is not None):
        invalid()
    region = data["region"]
    if region is not None:
        if not isinstance(region, dict) or set(region) != {"x", "y", "width", "height"}:
            invalid()
        if any(type(v) is not int or not 0 <= v <= 1000000 for v in region.values()):
            invalid()
        if region["width"] != width or region["height"] != height:
            invalid()
        if parent and (region["x"] + width > parent["pixels"]["width"] or
                       region["y"] + height > parent["pixels"]["height"]):
            invalid()
    if data["mode"] in ("region", "crop") and region is None:
        invalid()
    if data["mode"] == "viewport":
        viewport = data["viewport"]
        if viewport is None or region is not None or any(
                abs(data["pixels"][axis] - viewport[axis] * scale) > 1
                for axis in ("width", "height")):
            invalid()
    result.update(status="validated_claims", producer_claims=data)
    return result


def _natural_key(
        path: Path,
) -> tuple[tuple[tuple[int, int | str], ...], str, str]:
    natural = tuple(
        (0, int(part)) if part.isdigit() else (1, part.casefold())
        for part in re.split(r"(\d+)", path.name)
    )
    return natural, path.name.casefold(), path.name


def is_image_input(value: str) -> bool:
    path = Path(value).expanduser()
    return path.is_dir() or path.suffix.casefold() in SUPPORTED_EXTENSIONS | REJECTED_EXTENSIONS


def _ffprobe_image(path: Path) -> tuple[int, int]:
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-count_frames",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,nb_read_frames", "-of", "json",
                str(path.resolve()),
            ],
            capture_output=True, text=True,
        )
    except FileNotFoundError as ex:
        raise RuntimeError("ffprobe is not installed") from ex
    if result.returncode != 0:
        raise RuntimeError(
            f"ffprobe failed for {path.name}: "
            f"{result.stderr.strip() or 'invalid image'}"
        )
    try:
        stream = json.loads(result.stdout)["streams"][0]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as ex:
        raise RuntimeError(f"ffprobe failed for {path.name}: invalid image") from ex
    frame_value = stream.get("nb_read_frames")
    try:
        frame_count = int(frame_value)
    except (TypeError, ValueError) as ex:
        raise RuntimeError(
            f"ffprobe failed for {path.name}: expected exactly one frame, "
            f"reported {frame_value or 'unknown'}"
        ) from ex
    if frame_count != 1:
        raise RuntimeError(
            f"ffprobe failed for {path.name}: expected exactly one frame, "
            f"reported {frame_count}"
        )
    try:
        width, height = int(stream["width"]), int(stream["height"])
    except (KeyError, TypeError, ValueError) as ex:
        raise RuntimeError(f"ffprobe failed for {path.name}: invalid image") from ex
    if width <= 0 or height <= 0:
        raise RuntimeError(f"ffprobe failed for {path.name}: invalid image dimensions")
    return width, height


def _selected_paths(path: Path) -> tuple[list[Path], list[dict[str, str]]]:
    if path.is_file():
        if path.suffix.casefold() not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"unsupported image format: {path.suffix or '(none)'}")
        return [path], []

    selected: list[Path] = []
    skipped: list[dict[str, str]] = []
    for entry in sorted(path.iterdir(), key=_natural_key):
        if entry.is_symlink():
            skipped.append({"name": entry.name, "reason": "symlink"})
        elif not entry.is_file():
            skipped.append({"name": entry.name, "reason": "not a file"})
        elif entry.suffix.casefold() not in SUPPORTED_EXTENSIONS:
            skipped.append({"name": entry.name, "reason": "unsupported"})
        else:
            selected.append(entry)
    if not selected:
        raise ValueError(f"no supported images in folder: {path}")
    return selected, skipped


def probe(inp: str) -> dict[str, Any]:
    resolved = video.resolve_input(inp)
    path = Path(resolved).expanduser()
    if not path.exists():
        raise FileNotFoundError(video.describe_missing_input(resolved, kind="file or folder"))
    if path.is_symlink():
        raise ValueError(f"image input cannot be a symlink: {resolved}")
    if not path.is_file() and not path.is_dir():
        raise ValueError(f"image input is not a file or folder: {resolved}")

    selected, skipped = _selected_paths(path)
    images = []
    for index, source in enumerate(selected, start=1):
        width, height = _ffprobe_image(source)
        images.append({
            "index": index,
            "source": str(source.resolve()),
            "source_name": source.name,
            "width": width,
            "height": height,
            "bytes": source.stat().st_size,
            "provenance": _capture_provenance(source, width, height),
        })
    return {
        "source": "local",
        "input": str(path.resolve()),
        "kind": "image" if path.is_file() else "carousel",
        "item_count": len(images),
        "within_limit": len(images) <= MAX_IMAGES,
        "images": images,
        "skipped": skipped,
    }


def estimate(inp: str, out_words: int = 600,
             agent_model: str | None = None) -> dict[str, Any]:
    if out_words < 0:
        raise ValueError("out_words cannot be negative")
    info = probe(inp)
    if info["item_count"] > MAX_IMAGES:
        raise ValueError("image input has more than 100 items; choose a narrower folder")

    pricing = video.load_pricing()
    selected_model, model_rate, estimator = video._agent_rate(pricing, agent_model)
    target_width = int(pricing.get("frame", {}).get("target_width", 512))
    images = []
    for item in info["images"]:
        tokens = video.per_frame_tokens(
            item["width"], item["height"], target_width, estimator,
        )
        images.append({**item, "tokens": tokens})
    image_tokens = sum(item["tokens"] for item in images)
    output_tokens = round(out_words * 1.33)
    overhead_tokens = 2000
    read_tokens = image_tokens + overhead_tokens
    agent_usd = round(
        read_tokens / 1e6 * model_rate["input"]
        + output_tokens / 1e6 * model_rate["output"],
        4,
    )
    drivers_usd = {
        "images": image_tokens / 1e6 * model_rate["input"],
        "overhead": overhead_tokens / 1e6 * model_rate["input"],
        "output": output_tokens / 1e6 * model_rate["output"],
    }
    return {
        "input": info["input"],
        "source": "local",
        "kind": info["kind"],
        "item_count": info["item_count"],
        "images": images,
        "skipped": info["skipped"],
        "tokens": {
            "images": image_tokens,
            "output": output_tokens,
            "overhead": overhead_tokens,
            "read_total": read_tokens,
        },
        "cost_usd": {"transcription": 0.0, "agent": agent_usd, "total": agent_usd},
        "dominant_cost": max(drivers_usd, key=drivers_usd.get),
        "free": True,
        "needs_install": False,
        "requires_cloud_approval": False,
        "needs_model_download": False,
        "model_download": {"status": "not_applicable", "model": None},
        "agent_model": selected_model,
        "vision_estimator": estimator,
        "cost_basis": (
            "API-equivalent estimate; Codex subscription usage may not be billed per API token"
            if selected_model.startswith("gpt-5.6-") else "API token estimate"
        ),
    }


def run(inp: str, workdir: str | None = None) -> dict[str, Any]:
    return video.execute_read(_run, inp, workdir)


def _run(progress, inp, workdir):
    info = progress.call("probe", probe, inp)
    progress.begin("validate")
    if info["item_count"] > MAX_IMAGES:
        raise ValueError("image input has more than 100 items; choose a narrower folder")

    progress.complete("validate")
    progress.begin("workdir")
    destination = Path(workdir).expanduser() if workdir else Path(
        tempfile.mkdtemp(prefix="voidscape-images-")
    )
    if destination.is_symlink():
        raise ValueError(f"workdir cannot be a symlink: {destination}")
    if destination.exists():
        if not destination.is_dir() or any(destination.iterdir()):
            raise ValueError(f"workdir already exists and is not empty: {destination}")
    try:
        images_dir = destination / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
    except OSError as ex:
        raise RuntimeError(f"workdir creation failed: {ex}") from ex
    progress.complete("workdir")

    copied = []
    result = {
        "workdir": str(destination.resolve()),
        "kind": info["kind"], "source": info["source"], "input": info["input"],
        "item_count": info["item_count"], "images": copied, "skipped": info["skipped"],
        "content_trust": video.EVIDENCE_TRUST.copy(),
    }
    progress.result = result
    progress.begin("copy")
    for item in info["images"]:
        target = images_dir / f"{item['index']:03d}-{item['source_name']}"
        try:
            shutil.copy2(item["source"], target)
        except OSError as ex:
            raise RuntimeError(f"image copy failed: {ex}") from ex
        if _sha256(target) != item["provenance"]["importer_verified"]["sha256"]:
            raise ValueError("image changed after inspection; no completed manifest written")
        if _ffprobe_image(target) != (item["width"], item["height"]):
            raise ValueError("copied image dimensions changed; no completed manifest written")
        copied.append({
            "index": item["index"],
            "file": str(target.resolve()),
            "source_name": item["source_name"],
            "width": item["width"],
            "height": item["height"],
            "bytes": item["bytes"],
            "provenance": item["provenance"],
        })

    progress.complete("copy")
    return progress.finish(result, wrap_manifest_errors=True)


def _cli_manifest() -> dict[str, Any]:
    common = ["--human", "--envelope", "--compact"]
    return {
        "protocol_version": "1.0",
        "interactive": False,
        "commands": {
            "manifest": {"description": "describe the image CLI contract", "flags": common},
            "probe": {"description": "inspect a local image or folder", "flags": common},
            "estimate": {
                "description": "price image tokens before copying evidence",
                "flags": ["--out-words", "--agent-model", *common],
            },
            "run": {
                "description": "copy ordered images and write a manifest",
                "flags": ["--workdir", *common],
            },
        },
        "exit_codes": {
            "0": "success", "1": "unexpected_error", "2": "usage_error",
            "3": "input_error", "4": "approval_required", "5": "dependency_error",
            "6": "operation_failed",
        },
    }


def _fmt_estimate(result: dict[str, Any]) -> str:
    tokens, cost = result["tokens"], result["cost_usd"]
    return "\n".join([
        f"input: {result['input']}  ({result['kind']}, {result['item_count']} images)",
        f"agent={result['agent_model']}  vision={result['vision_estimator']}",
        f"  image tokens:  {tokens['images']:>8}",
        f"  output tokens: {tokens['output']:>8}",
        "  ---",
        f"  agent tokens: ${cost['agent']:.4f}",
        f"  TOTAL:        ${cost['total']:.4f}   (dominant: {result['dominant_cost']})",
        f"  basis: {result['cost_basis']}",
        _fmt_provenance(result),
    ])


def _fmt_provenance(result: dict[str, Any]) -> str:
    missing = sum(item.get("provenance", {}).get("status", "missing") == "missing"
                  for item in result["images"])
    return (f"  Capture provenance: {missing} missing; "
            f"{len(result['images']) - missing} validated claims (not authenticated). "
            "Coverage remains unknown.")


def _add_output_modes(parser: argparse.ArgumentParser) -> None:
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--human", action="store_true")
    modes.add_argument("--envelope", action="store_true")
    parser.add_argument("--compact", action="store_true")


def main(argv: list[str] | None = None) -> int:
    video.configure_cli_streams()
    args_list = list(sys.argv[1:] if argv is None else argv)
    commands = {"manifest", "probe", "estimate", "run"}
    command = next((arg for arg in args_list if arg in commands), None)
    video._AgentArgumentParser.machine_errors = "--envelope" in args_list
    video._AgentArgumentParser.compact_errors = "--compact" in args_list
    video._AgentArgumentParser.error_command = command

    parser = video._AgentArgumentParser(
        prog="image.py", description="local image and carousel evidence engine",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    manifest_parser = sub.add_parser("manifest")
    probe_parser = sub.add_parser("probe")
    probe_parser.add_argument("input")
    estimate_parser = sub.add_parser("estimate")
    estimate_parser.add_argument("input")
    estimate_parser.add_argument("--out-words", type=int, default=600)
    estimate_parser.add_argument("--agent-model")
    run_parser = sub.add_parser("run")
    run_parser.add_argument("input")
    run_parser.add_argument("--workdir")
    for child in (manifest_parser, probe_parser, estimate_parser, run_parser):
        _add_output_modes(child)

    args = parser.parse_args(args_list)
    try:
        if args.command == "manifest":
            result = _cli_manifest()
        elif args.command == "probe":
            result = probe(args.input)
        elif args.command == "estimate":
            result = estimate(args.input, args.out_words, args.agent_model)
        else:
            result = run(args.input, args.workdir)
        video._emit(result, args.human, args.envelope, args.compact, args.command,
                    formatter=_fmt_estimate)
    except Exception as ex:
        exit_code, code, retryable = video._classify_error(ex)
        if args.envelope:
            print(video._json_text(video.failure_envelope(ex, args.command), args.compact))
        else:
            print(video._json_text({"error": video.sanitize_error(ex)}, args.compact))
        return exit_code
    return 0


if __name__ == "__main__":
    sys.exit(main())
