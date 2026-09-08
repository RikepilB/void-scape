"""Read-only Instagram relationship audit from user-provided exports.

Diff a followers export against a following export and produce citable
evidence for unfollow decisions. This helper never touches the network, the
account, or the browser: the user exports both lists from Instagram's own
settings/data-download, and every output is a local report. Reading a
relationship never implies unfollowing; the suggested list is reviewed and
acted on by the human.

Contract (inspect -> preview -> process), mirroring capture_adapter:
- **inspect** — validate both export files and report counts. No writes.
- **preview** — the diff plan with category counts. No writes.
- **process** — write report.md + report.json into a new empty report dir.

Accepted inputs per side: an Instagram data-download JSON list
(``[{"value": "username", ...}, ...]``) or a plain text file with one handle
per line. Repository-only development helper; not installed with the skill.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from capture_adapter import CaptureError, emit_capture_error


MAX_HANDLES = 10000


def _normalize_handle(raw: str) -> str:
    return raw.strip().lstrip("@").casefold()


def load_handles(path: Path) -> list[str]:
    """Load one side of the relationship graph from an export file."""
    if not path.is_file():
        raise CaptureError(f"export file not found: {path}")
    text = path.read_text(encoding="utf-8", errors="replace")
    handles: list[str] = []
    stripped = text.strip()
    if stripped.startswith("["):
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError as ex:
            raise CaptureError(f"export is not valid JSON: {path.name}") from ex
        if not isinstance(data, list):
            raise CaptureError(f"export JSON must be a list: {path.name}")
        for item in data:
            if isinstance(item, dict) and isinstance(item.get("value"), str):
                handles.append(_normalize_handle(item["value"]))
            elif isinstance(item, str):
                handles.append(_normalize_handle(item))
    else:
        handles = [_normalize_handle(line) for line in text.splitlines() if line.strip()]
    seen: list[str] = []
    for handle in handles:
        if handle and handle not in seen:
            seen.append(handle)
    if not seen:
        raise CaptureError(f"export contains no handles: {path.name}")
    if len(seen) > MAX_HANDLES:
        raise CaptureError(f"export exceeds the {MAX_HANDLES}-handle limit: {path.name}")
    return seen


def diff_relationships(followers: list[str], following: list[str]) -> dict[str, Any]:
    follower_set = set(followers)
    following_set = set(following)
    mutual = sorted(follower_set & following_set)
    not_following_back = sorted(following_set - follower_set)
    you_dont_follow_back = sorted(follower_set - following_set)
    return {
        "mutual": mutual,
        "not_following_back": not_following_back,
        "you_dont_follow_back": you_dont_follow_back,
        "counts": {
            "followers": len(follower_set),
            "following": len(following_set),
            "mutual": len(mutual),
            "not_following_back": len(not_following_back),
            "you_dont_follow_back": len(you_dont_follow_back),
        },
    }


def inspect(followers_path: Path, following_path: Path) -> dict[str, Any]:
    followers = load_handles(followers_path)
    following = load_handles(following_path)
    return {
        "followers_file": str(followers_path.resolve()),
        "following_file": str(following_path.resolve()),
        "followers": len(followers),
        "following": len(following),
        "mutates_source": False,
        "network_access": False,
    }


def preview(followers_path: Path, following_path: Path) -> dict[str, Any]:
    diff = diff_relationships(load_handles(followers_path), load_handles(following_path))
    counts = diff["counts"]
    return {
        "action": "write_local_report",
        "mutates_source": False,
        "network_access": False,
        "never_unfollows": True,
        "counts": counts,
        "suggested_review_list": "not_following_back",
        "suggested_review_count": counts["not_following_back"],
    }


def process(followers_path: Path, following_path: Path, report_dir: Path) -> dict[str, Any]:
    if report_dir.is_symlink():
        raise CaptureError(f"report dir cannot be a symlink: {report_dir}")
    if report_dir.exists():
        if not report_dir.is_dir() or any(report_dir.iterdir()):
            raise CaptureError(f"report dir already exists and is not empty: {report_dir}")
    diff = diff_relationships(load_handles(followers_path), load_handles(following_path))
    counts = diff["counts"]

    try:
        report_dir.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Instagram relationship audit",
            "",
            "Read-only diff of two user-provided exports. Nothing was unfollowed,",
            "followed, or messaged; acting on this list is a separate human decision.",
            "",
            f"- followers: {counts['followers']}",
            f"- following: {counts['following']}",
            f"- mutual: {counts['mutual']}",
            f"- not following you back: {counts['not_following_back']}",
            f"- you do not follow back: {counts['you_dont_follow_back']}",
            "",
            "## Suggested review (not following you back) — cite as [user N]",
            "",
        ]
        for index, handle in enumerate(diff["not_following_back"], start=1):
            lines.append(f"{index}. {handle} — [user {index}]")
        lines += [
            "",
            "## You do not follow back",
            "",
        ]
        for index, handle in enumerate(diff["you_dont_follow_back"], start=1):
            lines.append(f"{index}. {handle}")
        (report_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

        result = {
            "report_dir": str(report_dir.resolve()),
            "report": str((report_dir / "report.md").resolve()),
            "counts": counts,
            "not_following_back": diff["not_following_back"],
            "you_dont_follow_back": diff["you_dont_follow_back"],
            "mutual_count": counts["mutual"],
            "mutates_source": False,
            "network_access": False,
            "never_unfollows": True,
            "citation_guide": "cite each suggested handle with user N, e.g. [user 1]",
        }
        (report_dir / "report.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    except OSError as ex:
        raise CaptureError(f"report write failed: {ex}") from ex
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ig_follow_audit_helper",
        description="read-only Instagram relationship audit from user-provided exports",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("inspect", "preview"):
        child = sub.add_parser(name)
        child.add_argument("--followers", required=True)
        child.add_argument("--following", required=True)
    process_parser = sub.add_parser("process")
    process_parser.add_argument("--followers", required=True)
    process_parser.add_argument("--following", required=True)
    process_parser.add_argument("--report-dir", required=True)
    args = parser.parse_args(argv)

    try:
        followers_path = Path(args.followers).expanduser()
        following_path = Path(args.following).expanduser()
        if args.command == "inspect":
            result = inspect(followers_path, following_path)
        elif args.command == "preview":
            result = preview(followers_path, following_path)
        else:
            result = process(
                followers_path, following_path, Path(args.report_dir).expanduser()
            )
    except CaptureError as err:
        return emit_capture_error(err)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
