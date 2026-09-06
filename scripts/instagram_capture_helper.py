"""Deterministic helper for the Instagram capture pipeline: shortcode extraction,
canonical URL building, dedup checking, and confirmed append to read-video's
inbox_dir/urls.md queue. No network, no browser — the capture subagent shells
out to this for every reel so the fragile parsing/append logic never depends
on freeform agent judgment."""
import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from capture_adapter import (
    append_and_confirm as append_and_confirm,
    is_duplicate as is_duplicate,
    queue_append_result,
)

_ALLOWED_HOSTS = {"instagram.com", "www.instagram.com"}
_PATH_RE = re.compile(r"^/(?:reel|p|tv)/([A-Za-z0-9_-]+)")
_SHORTCODE_RE = re.compile(r"^[A-Za-z0-9_-]{5,15}$")


def extract_shortcode(url_or_code: str) -> str:
    s = url_or_code.strip()
    if _SHORTCODE_RE.match(s):
        return s
    parsed = urlparse(s)
    if parsed.hostname and parsed.hostname.lower() in _ALLOWED_HOSTS:
        m = _PATH_RE.match(parsed.path)
        if m:
            return m.group(1)
    raise ValueError(f"not a recognizable Instagram reel/post URL or shortcode: {url_or_code!r}")


def canonical_url(shortcode: str) -> str:
    return f"https://www.instagram.com/reel/{shortcode}/"


def process(url_or_code: str, urls_md_path: Path) -> dict:
    url = canonical_url(extract_shortcode(url_or_code))
    write = queue_append_result(url, urls_md_path)
    safe_to_unsave = write["appended"] or write["duplicate"]
    return {
        "url": url,
        "duplicate": write["duplicate"],
        "appended": write["appended"],
        "safe_to_unsave": safe_to_unsave,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="instagram_capture_helper")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("process", help="canonicalize, dedup-check, and append a reel URL")
    p.add_argument("url_or_code")
    p.add_argument("urls_md_path")
    args = parser.parse_args(argv)

    if args.command == "process":
        try:
            result = process(args.url_or_code, Path(args.urls_md_path))
        except ValueError as e:
            print(json.dumps({"error": str(e)}))
            return 1
        print(json.dumps(result))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
