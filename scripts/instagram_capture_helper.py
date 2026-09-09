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
    CaptureError,
    append_and_confirm as append_and_confirm,
    is_duplicate as is_duplicate,
    queue_append_result,
    preview_action_for_url,
)

_ALLOWED_HOSTS = {"instagram.com", "www.instagram.com"}
_PATH_RE = re.compile(r"^/(?:reel|p|tv)/([A-Za-z0-9_-]{5,15})/?$")
_SHORTCODE_RE = re.compile(r"^[A-Za-z0-9_-]{5,15}$")


def extract_shortcode(url_or_code: str) -> str:
    if any(ord(character) < 32 or ord(character) == 127 for character in url_or_code):
        raise ValueError("Instagram input contains control characters")
    s = url_or_code.strip()
    if _SHORTCODE_RE.match(s):
        return s
    parsed = urlparse(s)
    if (parsed.scheme in {'http', 'https'} and parsed.hostname and
            parsed.hostname.lower() in _ALLOWED_HOSTS and parsed.username is None and
            parsed.password is None and parsed.port is None):
        m = _PATH_RE.match(parsed.path)
        if m:
            return m.group(1)
    raise ValueError("not a recognizable Instagram reel/post URL or shortcode")


def canonical_url(shortcode: str) -> str:
    if not _SHORTCODE_RE.fullmatch(shortcode):
        raise ValueError('invalid Instagram shortcode')
    return f"https://www.instagram.com/reel/{shortcode}/"


def inspect_url(url_or_code: str) -> dict:
    shortcode = extract_shortcode(url_or_code)
    return {'shortcode': shortcode, 'url': canonical_url(shortcode),
            'mutates_urls_md': False, 'mutates_source': False}


def preview(url_or_code: str, urls_md_path: Path) -> dict:
    result = inspect_url(url_or_code)
    duplicate, action = preview_action_for_url(result['url'], urls_md_path)
    return {**result, 'duplicate': duplicate, 'action': action}


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
    p = sub.add_parser('inspect', help='validate and canonicalize one URL without writing')
    p.add_argument('url_or_code')
    p = sub.add_parser('preview', help='preview a queue append without writing')
    p.add_argument('url_or_code')
    p.add_argument('urls_md_path')
    args = parser.parse_args(argv)

    try:
        if args.command == 'inspect':
            result = inspect_url(args.url_or_code)
        elif args.command == 'preview':
            result = preview(args.url_or_code, Path(args.urls_md_path))
        else:
            result = process(args.url_or_code, Path(args.urls_md_path))
    except (ValueError, OSError, CaptureError):
        print(json.dumps({'error': 'Instagram capture validation or queue operation failed'}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
