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


def is_duplicate(url: str, urls_md_path: Path) -> bool:
    if not urls_md_path.exists():
        return False
    lines = urls_md_path.read_text(encoding="utf-8").splitlines()
    return url in (line.strip() for line in lines)


def append_and_confirm(url: str, urls_md_path: Path) -> bool:
    urls_md_path.parent.mkdir(parents=True, exist_ok=True)
    with urls_md_path.open("a", encoding="utf-8") as f:
        f.write(url + "\n")
    lines = urls_md_path.read_text(encoding="utf-8").splitlines()
    return url in (line.strip() for line in lines)


def process(url_or_code: str, urls_md_path: Path) -> dict:
    url = canonical_url(extract_shortcode(url_or_code))
    if is_duplicate(url, urls_md_path):
        return {"url": url, "duplicate": True, "appended": False, "safe_to_unsave": True}
    appended = append_and_confirm(url, urls_md_path)
    return {"url": url, "duplicate": False, "appended": appended, "safe_to_unsave": appended}


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
