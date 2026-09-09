"""Foreground batches compose existing readers without retaining authorization."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from pathlib import Path

if __package__:
    from . import video
else:
    import video

MAX_BYTES = 1024 * 1024
MAX_ITEMS = 100
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
FORBIDDEN = {"workdir", "config", "allow_cloud", "allow_model_download", "json"}
GENERAL = {"input", "id", "reader", "out_words", "agent_model"}


def _no_links(path):
    for candidate in (*reversed(path.parents), path):
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            continue
        if candidate.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("batch paths cannot contain links or reparse points")


def _local_path(value, base, *, check=True):
    path = Path(value).expanduser()
    path = Path(os.path.abspath(path if path.is_absolute() else base / path))
    if check:
        _no_links(path)
        if not path.exists():
            raise ValueError("batch local input or reference does not exist")
    return str(path)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key in batch manifest")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError("batch numbers must be finite")


def _validate_value(action, value):
    if isinstance(action, argparse._StoreTrueAction):
        valid = type(value) is bool
    elif action.type is int:
        valid = type(value) is int
    elif action.type is float:
        valid = type(value) in {float, int} and math.isfinite(value)
    else:
        valid = isinstance(value, str) and len(value) <= 4096
    if not valid or (action.choices is not None and value not in action.choices):
        raise ValueError("invalid batch reader option type or value")


def load(manifest, cli):
    path = Path(os.path.abspath(Path(manifest).expanduser()))
    _no_links(path)
    if not path.is_file():
        raise ValueError("batch manifest must be a local JSONL file")
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("batch manifest exceeds 1 MiB")
    parser = argparse.ArgumentParser(add_help=False)
    cli._add_analysis_options(parser, include_run=True)
    actions = {action.dest: action for action in parser._actions
               if action.dest not in FORBIDDEN}
    items, identifiers = [], set()
    for line_number, line in enumerate(raw.decode("utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line, object_pairs_hook=_pairs, parse_constant=_invalid_constant)
        if not isinstance(row, dict) or not isinstance(row.get("input"), str) or not row["input"].strip():
            raise ValueError("batch rows require a nonempty input string")
        if len(items) >= MAX_ITEMS:
            raise ValueError("batch manifest exceeds 100 items")
        if any(key not in actions and key != "id" for key in row):
            raise ValueError("unknown or forbidden field in batch manifest")
        identifier = row.get("id", f"item{len(items) + 1:03d}")
        if not isinstance(identifier, str) or not ID.fullmatch(identifier):
            raise ValueError("batch IDs must be 1..64 ASCII letters, digits, underscores or hyphens")
        if identifier.casefold() in identifiers:
            raise ValueError("batch IDs must be unique, ignoring case")
        identifiers.add(identifier.casefold())
        args = parser.parse_args(["--", row["input"]])
        for key, value in row.items():
            if key != "id":
                _validate_value(actions[key], value)
                setattr(args, key, value)
        if args.frames is not None and args.frames <= 0:
            raise ValueError("batch frame counts must be positive")
        if args.out_words < 0:
            raise ValueError("batch output word estimates cannot be negative")
        if not video.is_url(args.input):
            args.input = _local_path(args.input, path.parent)
        if args.align_reference:
            args.align_reference = _local_path(args.align_reference, path.parent,
                                               check=args.stop_at is None)
        reader = cli._select_reader(args.input, args.reader)
        if reader != "video" and set(row) - GENERAL:
            raise ValueError("video-only options supplied for another batch reader")
        items.append({"id": identifier, "line": line_number, "args": args, "reader": reader})
    if not items:
        raise ValueError("batch manifest contains no items")
    return {"manifest_sha256": hashlib.sha256(raw).hexdigest(), "items": items}


def _scope(args, estimate):
    if args.stop_at == "probe":
        return
    duration = estimate.get("duration_s") or 0.0
    end = args.end if args.end is not None else duration
    if args.start < 0 or end <= args.start or (duration and end > duration):
        raise ValueError("invalid batch video time window")
    if args.timestamps:
        for value in args.timestamps.split(","):
            timestamp = video._parse_timestamp(value)
            if not args.start <= timestamp <= end:
                raise ValueError("batch pinned timestamp is outside the selected window")


def prepare(manifest, workspace, cli):
    plan = load(manifest, cli)
    for item in plan["items"]:
        reader, estimate = cli._preview_data(item["args"], workspace)
        if reader != item["reader"]:
            raise ValueError("batch source routing changed during preflight")
        if reader == "video":
            _scope(item["args"], estimate)
        item["estimate"] = estimate
    return plan


def preview_result(plan):
    items, gates = [], []
    costs = {"transcription": 0.0, "agent": 0.0, "total": 0.0}
    for item in plan["items"]:
        estimate = item["estimate"]
        items.append({"id": item["id"], "line": item["line"], "reader": item["reader"],
                      "estimate": estimate})
        for field in costs:
            costs[field] += estimate.get("cost_usd", {}).get(field, 0.0)
        for field, kind in (("requires_cloud_approval", "cloud_approval"),
                            ("needs_model_download", "model_download")):
            if estimate.get(field):
                gates.append({"id": item["id"], "type": kind})
    return {"manifest_sha256": plan["manifest_sha256"], "total": len(items),
            "items": items, "gates": gates,
            "cost_usd": {key: round(value, 6) for key, value in costs.items()},
            "content_trust": video.EVIDENCE_TRUST.copy()}


def _check_permissions(plan, allow_cloud, allow_model_download):
    for field, allowed, kind in (("requires_cloud_approval", allow_cloud, "cloud_approval"),
                                 ("needs_model_download", allow_model_download, "model_download")):
        blocked = [item["id"] for item in plan["items"] if item["estimate"].get(field)]
        if blocked and not allowed:
            error = video.ApprovalRequired(
                "batch requires explicit permission; review batch-preview before reading", kind, "batch")
            error.gate["items"] = blocked
            raise error
    if any(item["estimate"].get("needs_install") for item in plan["items"]):
        raise RuntimeError("a selected batch backend is not installed")


def _identity(root):
    _no_links(root)
    info = root.stat()
    if not root.is_dir():
        raise ValueError("batch output root changed type")
    return info.st_dev, info.st_ino


def _boundary(root, identity, child=None):
    if _identity(root) != identity:
        raise ValueError("batch output root was replaced")
    if child is not None:
        _no_links(child)
        child.relative_to(root)


def _save_summary(root, identity, summary):
    _boundary(root, identity)
    staged = root / "batch-summary.next.json"
    with staged.open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    _boundary(root, identity)
    staged.replace(root / "batch-summary.json")


def read(manifest, output, workspace, cli, *, allow_cloud=False, allow_model_download=False):
    root = Path(os.path.abspath(Path(output).expanduser()))
    _no_links(root)
    if root.exists():
        raise ValueError("batch output root must not already exist")
    plan = prepare(manifest, workspace, cli)
    _check_permissions(plan, allow_cloud, allow_model_download)
    _no_links(root)
    root.mkdir(parents=True, exist_ok=False)
    identity = _identity(root)
    summary = {"manifest_sha256": plan["manifest_sha256"], "workdir": str(root),
               "status": "running", "total": len(plan["items"]), "completed": 0,
               "stopped": 0, "failed": 0, "items": [], "content_trust": video.EVIDENCE_TRUST.copy()}
    _save_summary(root, identity, summary)
    for index, item in enumerate(plan["items"], 1):
        child = root / f"{index:03d}-{item['id']}"
        _boundary(root, identity, child)
        args = item["args"]
        args.workdir = str(child)
        args.allow_cloud = allow_cloud
        args.allow_model_download = allow_model_download
        try:
            reader, result = cli._read_data(args, workspace)
            if reader != item["reader"] or Path(result["workdir"]).resolve() != child:
                raise ValueError("batch reader returned an unexpected output boundary")
            if result.get("status") not in {"complete", "stopped"}:
                raise RuntimeError("batch reader did not confirm a completed or deliberately stopped result")
            outcome = video._envelope(result, None, "read")
        except Exception as error:
            outcome = video.failure_envelope(error, "read")
        _boundary(root, identity, child)
        status = ("failed" if not outcome["ok"] else
                  "stopped" if outcome["data"].get("status") == "stopped" else "completed")
        summary[status] += 1
        summary["items"].append({"id": item["id"], "line": item["line"],
                                 "reader": item["reader"], "status": status, "result": outcome})
        _save_summary(root, identity, summary)
    summary["status"] = "failed" if summary["failed"] else "completed_with_stops" if summary["stopped"] else "complete"
    _save_summary(root, identity, summary)
    return summary
