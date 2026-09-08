"""Machine-readable source routing and capability truth for Voidscape."""
from __future__ import annotations

import ipaddress
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
ARTICLE_EXTENSIONS = {".html", ".htm", ".md", ".markdown", ".txt", ".xml", ".rss", ".atom"}
MEDIA_EXTENSIONS = {
    ".3gp", ".aac", ".flac", ".m4a", ".m4v", ".mkv", ".mov", ".mp3", ".mp4",
    ".mpeg", ".mpg", ".ogg", ".opus", ".wav", ".webm", ".wma", ".wmv",
}
# Minimal detection twin of chat.looks_like_chat_export; the registry stays
# reader-independent, so the full parser lives in chat.py.
CHAT_HEADER_RE = re.compile(r"^\[[^\]]{4,40}\]\s?\S")


def _looks_like_chat_export(path: Path) -> bool:
    try:
        sample = path.read_text(encoding="utf-8", errors="replace")[:8192]
    except OSError:
        return False
    matches = 0
    for line in sample.splitlines():
        if CHAT_HEADER_RE.match(line):
            matches += 1
            if matches >= 2:
                return True
    return False


PLATFORM_PROFILES: tuple[dict[str, Any], ...] = (
    {
        "id": "youtube",
        "domains": ["youtube.com", "youtu.be"],
        "default_reader": "video",
        "reader_options": ["video"],
        "public_read": "best_effort",
        "capture": "dev_only_official_api",
        "note": "Public URLs use yt-dlp. Private queue capture uses explicit OAuth and is not installed.",
    },
    {
        "id": "instagram",
        "domains": ["instagram.com"],
        "default_reader": "video",
        "reader_options": ["video", "article"],
        "public_read": "best_effort",
        "capture": "dev_only_browser_observed",
        "note": "Reels are media-first; posts/carousels may need permitted browser selection and local images.",
    },
    {
        "id": "tiktok",
        "domains": ["tiktok.com"],
        "default_reader": "video",
        "reader_options": ["video"],
        "public_read": "best_effort",
        "capture": "not_shipped",
        "note": "Direct public media may work through yt-dlp; saved collections remain harness-owned.",
    },
    {
        "id": "x-twitter",
        "domains": ["x.com", "twitter.com"],
        "default_reader": "video",
        "reader_options": ["video", "article"],
        "public_read": "best_effort",
        "capture": "not_shipped",
        "note": "Use video for media/Spaces and --reader article for text-first public threads.",
    },
    {
        "id": "reddit",
        "domains": ["reddit.com", "redd.it", "v.redd.it"],
        "default_reader": "article",
        "reader_options": ["article", "video"],
        "public_read": "best_effort",
        "capture": "not_shipped",
        "note": "Reddit posts are mixed media; use --reader video when the selected post is media-first.",
    },
    {
        "id": "linkedin",
        "domains": ["linkedin.com"],
        "default_reader": "article",
        "reader_options": ["article", "video"],
        "public_read": "best_effort",
        "capture": "not_shipped",
        "note": "Most pages require signed-in browser selection; Voidscape never imports that session.",
    },
    {
        "id": "substack",
        "domains": ["substack.com"],
        "default_reader": "article",
        "reader_options": ["article", "video"],
        "public_read": "shipped_with_fetch_approval",
        "capture": "rss_or_direct_url",
        "note": "Public articles and RSS/Atom feeds use the article reader; subscriber pages stay browser-owned.",
    },
    {
        "id": "facebook",
        "domains": ["facebook.com", "fb.watch"],
        "default_reader": "video",
        "reader_options": ["video", "article"],
        "public_read": "best_effort",
        "capture": "not_shipped",
        "note": "Public media may work through yt-dlp; authenticated collections are not automated.",
    },
    {
        "id": "vimeo",
        "domains": ["vimeo.com"],
        "default_reader": "video",
        "reader_options": ["video"],
        "public_read": "best_effort",
        "capture": "direct_url_only",
        "note": "Direct public media uses the video reader.",
    },
    {
        "id": "twitch",
        "domains": ["twitch.tv"],
        "default_reader": "video",
        "reader_options": ["video"],
        "public_read": "best_effort",
        "capture": "direct_url_only",
        "note": "Public VODs/clips use the video reader when supported by yt-dlp.",
    },
    {
        "id": "dailymotion",
        "domains": ["dailymotion.com", "dai.ly"],
        "default_reader": "video",
        "reader_options": ["video"],
        "public_read": "best_effort",
        "capture": "direct_url_only",
        "note": "Direct public media uses the video reader.",
    },
    {
        "id": "soundcloud",
        "domains": ["soundcloud.com"],
        "default_reader": "video",
        "reader_options": ["video"],
        "public_read": "best_effort",
        "capture": "direct_url_only",
        "note": "Audio uses the video/audio reader with --tier audio.",
    },
)


def _domain_matches(hostname: str, domain: str) -> bool:
    return hostname == domain or hostname.endswith(f".{domain}")


def _profile_for_host(hostname: str) -> dict[str, Any] | None:
    normalized = hostname.casefold().rstrip(".")
    for profile in PLATFORM_PROFILES:
        if any(_domain_matches(normalized, domain) for domain in profile["domains"]):
            return profile
    return None


def _web_route(value: str) -> dict[str, Any]:
    parsed = urlsplit(value)
    hostname = (parsed.hostname or "").casefold().rstrip(".")
    suffix = Path(parsed.path).suffix.casefold()
    profile = _profile_for_host(hostname)
    path_parts = parsed.path.strip("/").split("/")
    platform = profile["id"] if profile else "generic-web"
    account_collection = (
        (platform == "linkedin" and parsed.path.rstrip("/") == "/my-items/saved-posts")
        or (platform == "youtube" and parsed.path.rstrip("/") == "/feed/playlists")
        or (platform == "instagram" and len(path_parts) == 3
            and path_parts[1:] == ["saved", "all-posts"])
    )
    if account_collection:
        return {
            "source": "url",
            "platform": platform,
            "default_reader": None,
            "reader_options": [],
            "public_read": "not_supported",
            "capture": profile["capture"],
            "note": "Account collection page: select one permitted item in the signed-in browser, then pass its URL or local evidence. Voidscape does not import browser authentication.",
            "requires_network": True,
            "requires_browser_auth": True,
        }
    if suffix in IMAGE_EXTENSIONS:
        default_reader = None
        reader_options: list[str] = []
        note = "Remote image fetch is not shipped; save the permitted image locally or use a permitted tab screenshot."
    elif suffix in MEDIA_EXTENSIONS:
        default_reader = "video"
        reader_options = ["video"]
        note = "Direct media URL uses the video/audio reader when the remote server permits access."
    elif suffix in {".rss", ".atom", ".xml"}:
        default_reader = "article"
        reader_options = ["article"]
        note = "Remote feed fetch requires explicit approval and public-network validation."
    elif profile:
        default_reader = profile["default_reader"]
        reader_options = list(profile["reader_options"])
        note = profile["note"]
    else:
        default_reader = "article"
        reader_options = ["article", "video"]
        note = "Generic pages default to article; use --reader video only for a known direct media page."

    return {
        "source": "url",
        "platform": profile["id"] if profile else "generic-web",
        "default_reader": default_reader,
        "reader_options": reader_options,
        "public_read": profile["public_read"] if profile else "best_effort",
        "capture": profile["capture"] if profile else "direct_url_only",
        "note": note,
        "requires_network": True,
        "requires_browser_auth": False,
    }


def _web_input_error(value: str) -> str | None:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return "Web input is malformed."
    if not parsed.hostname:
        return "Web input must include a hostname."
    if parsed.username is not None or parsed.password is not None:
        return "Web input cannot contain credentials."
    if parsed.fragment:
        return "Web input cannot contain a fragment; select the canonical page URL."
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        return "Web input cannot contain control characters."
    expected_port = 443 if parsed.scheme.casefold() == "https" else 80
    if port not in {None, expected_port}:
        return "Web input must use its standard port 80 or 443."
    hostname = parsed.hostname.casefold().rstrip(".")
    if hostname == "localhost" or hostname.endswith(".localhost"):
        return "Web input cannot target localhost or a private network."
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        try:
            hostname.encode("ascii")
        except UnicodeEncodeError:
            return "Web input hostname must use ASCII or IDNA form."
    else:
        if not address.is_global:
            return "Web input cannot target localhost or a private network."
    return None


def _reported_input(value: str) -> tuple[str, bool]:
    """Keep credential/query material out of route output and agent logs."""
    try:
        parsed = urlsplit(value)
        if parsed.scheme.casefold() not in {"http", "https"} or not parsed.hostname:
            return "[rejected input]", True
        host = parsed.hostname.casefold().rstrip(".")
        if ":" in host:
            host = f"[{host}]"
        try:
            port = parsed.port
        except ValueError:
            return "[rejected input]", True
        expected_port = 443 if parsed.scheme.casefold() == "https" else 80
        netloc = host if port in {None, expected_port} else f"{host}:{port}"
        sanitized = parsed._replace(netloc=netloc, query="", fragment="").geturl()
        return sanitized, sanitized != value
    except (TypeError, ValueError):
        return "[rejected input]", True


def route(value: str) -> dict[str, Any]:
    stripped = value.strip()
    parse_error = False
    try:
        parsed = urlsplit(stripped)
    except ValueError:
        parse_error = True
        parsed = urlsplit("")
    if parse_error:
        selected = {
            "source": "unsupported",
            "platform": "unsupported",
            "default_reader": None,
            "reader_options": [],
            "public_read": "not_supported",
            "capture": "not_supported",
            "note": "Web input is malformed.",
            "requires_network": False,
            "requires_browser_auth": False,
        }
    elif not stripped:
        selected = {
            "source": "unsupported",
            "platform": "unsupported",
            "default_reader": None,
            "reader_options": [],
            "public_read": "not_supported",
            "capture": "not_supported",
            "note": "Input must be a non-empty local path or HTTP(S) URL.",
            "requires_network": False,
            "requires_browser_auth": False,
        }
    elif parsed.scheme.casefold() in {"http", "https"}:
        web_error = _web_input_error(stripped)
        if web_error:
            selected = {
                "source": "unsupported",
                "platform": "unsupported",
                "default_reader": None,
                "reader_options": [],
                "public_read": "not_supported",
                "capture": "not_supported",
                "note": web_error,
                "requires_network": False,
                "requires_browser_auth": False,
            }
        else:
            selected = _web_route(stripped)
    elif parsed.scheme and not (
        len(parsed.scheme) == 1 and len(stripped) > 2 and stripped[1] == ":"
    ):
        selected = {
            "source": "unsupported",
            "platform": "unsupported",
            "default_reader": None,
            "reader_options": [],
            "public_read": "not_supported",
            "capture": "not_supported",
            "note": "Network inputs must use http or https; file, data, javascript, and other schemes are rejected.",
            "requires_network": False,
            "requires_browser_auth": False,
        }
    else:
        path = Path(stripped).expanduser()
        suffix = path.suffix.casefold()
        if path.is_dir():
            reader = "image"
            note = "A local directory is treated as one non-recursive, naturally ordered carousel."
        elif suffix in IMAGE_EXTENSIONS:
            reader = "image"
            note = "Local image evidence is copied byte-for-byte."
        elif suffix == ".txt" and path.is_file() and _looks_like_chat_export(path):
            reader = "chat"
            note = "WhatsApp-style chat export evidence stays local; media files are referenced, not extracted."
        elif suffix in ARTICLE_EXTENSIONS:
            reader = "article"
            note = "Local article/feed evidence stays local."
        else:
            reader = "video"
            note = "Local video/audio is inspected by the media reader."
        selected = {
            "source": "local",
            "platform": "local",
            "default_reader": reader,
            "reader_options": [reader],
            "public_read": "not_applicable",
            "capture": "not_applicable",
            "note": note,
            "requires_network": False,
            "requires_browser_auth": False,
        }
    is_windows_drive = (
        len(parsed.scheme) == 1 and len(stripped) > 2 and stripped[1] == ":"
    )
    if parse_error or (
        selected["source"] == "unsupported" and parsed.scheme and not is_windows_drive
    ):
        reported_input, input_redacted = "[rejected input]", True
    elif parsed.scheme.casefold() in {"http", "https"}:
        reported_input, input_redacted = _reported_input(stripped)
    else:
        reported_input, input_redacted = stripped, False
    return {
        "schema_version": "1.0",
        "input": reported_input,
        "input_redacted": input_redacted,
        **selected,
        "boundaries": {
            "inspect_preview_read": True,
            "browser_session_import": False,
            "source_content_trusted": False,
            "route_output_strips_url_secrets": True,
        },
    }


def manifest() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "readers": {
            "video": "local media and best-effort public media URLs",
            "image": "local images and filename-ordered carousel folders",
            "article": "local documents/feeds and approved public article/feed fetches",
            "chat": "local WhatsApp-style chat export files",
        },
        "platforms": [dict(profile) for profile in PLATFORM_PROFILES],
        "generic_web": {
            "default_reader": "article",
            "reader_override": "video",
            "remote_images": "save locally or capture a permitted tab screenshot",
        },
        "boundaries": {
            "capture_is_separate_from_reading": True,
            "browser_and_account_access_belong_to_harness": True,
            "browser_credentials_cookies_storage_read": False,
            "source_content_trusted": False,
            "platform_compatibility_is_not_universal": True,
            "route_output_strips_url_secrets": True,
        },
    }
