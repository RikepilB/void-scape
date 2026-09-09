"""Local article, HTML, Markdown, and RSS/Atom evidence engine."""
from __future__ import annotations

import argparse
import hashlib
import html
import http.client
import ipaddress
import json
import re
import socket
import ssl
import sys
import tempfile
import urllib.error
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit
from urllib.request import Request
from xml.etree import ElementTree as ET

if __package__:
    from . import video
else:
    import video


ARTICLE_EXTENSIONS = {".html", ".htm", ".md", ".markdown", ".txt"}
FEED_EXTENSIONS = {".xml", ".rss", ".atom"}
SUPPORTED_EXTENSIONS = ARTICLE_EXTENSIONS | FEED_EXTENSIONS
MAX_ENTRIES = 100
DEFAULT_URL_WORDS = 1200
MAX_REMOTE_BYTES = 5 * 1024 * 1024
MAX_REDIRECTS = 5
ALLOWED_REMOTE_PORTS = {80, 443}
REMOTE_CONTENT_TYPES = {
    "application/atom+xml",
    "application/rss+xml",
    "application/xhtml+xml",
    "application/xml",
    "text/html",
    "text/plain",
    "text/xml",
}
VIDEO_HOST_RE = re.compile(
    r"^https?://(?:www\.)?(?:"
    r"youtube\.com|youtu\.be|vimeo\.com|twitch\.tv|"
    r"instagram\.com|tiktok\.com|twitter\.com|x\.com|"
    r"facebook\.com|fb\.watch|dailymotion\.com|soundcloud\.com"
    r")(?:/|$)",
    re.I,
)
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_STYLE_RE = re.compile(
    r"<(script|style)\b[^>]*>.*?</\1>",
    re.I | re.DOTALL,
)
WHITESPACE_RE = re.compile(r"\s+")
ATOM_NS = "http://www.w3.org/2005/Atom"


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host: str, port: int, pinned_address: str, timeout: float):
        self._pinned_address = pinned_address
        super().__init__(host, port=port, timeout=timeout)

    def connect(self):
        self.sock = socket.create_connection(
            (self._pinned_address, self.port),
            self.timeout,
            self.source_address,
        )


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, port: int, pinned_address: str, timeout: float):
        self._pinned_address = pinned_address
        super().__init__(host, port=port, timeout=timeout, context=ssl.create_default_context())

    def connect(self):
        raw_socket = socket.create_connection(
            (self._pinned_address, self.port),
            self.timeout,
            self.source_address,
        )
        try:
            self.sock = self._context.wrap_socket(raw_socket, server_hostname=self.host)
        except Exception:
            raw_socket.close()
            raise


class _PinnedResponse:
    def __init__(self, response, connection):
        self._response = response
        self._connection = connection
        self.headers = response.headers

    def read(self, size=-1):
        return self._response.read(size)

    def close(self):
        try:
            self._response.close()
        finally:
            self._connection.close()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()
        return False


def _validated_target(url: str, *, resolver=None):
    if not isinstance(url, str) or not url or len(url) > 4096:
        raise ValueError("remote article URL must be a bounded non-empty string")
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as ex:
        raise ValueError(f"remote article URL is invalid: {ex}") from ex
    if parsed.scheme.casefold() not in {"http", "https"}:
        raise ValueError("remote article URL must use http or https")
    if not parsed.hostname:
        raise ValueError("remote article URL must include a hostname")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("remote article URL cannot include credentials")
    if any(ord(character) < 32 or ord(character) == 127 for character in url):
        raise ValueError("remote article URL cannot contain control characters")
    try:
        parsed.hostname.encode("ascii")
    except UnicodeEncodeError as ex:
        raise ValueError("remote article hostname must use ASCII or IDNA form") from ex
    if parsed.fragment:
        url = parsed._replace(fragment="").geturl()
        parsed = urlsplit(url)

    expected_port = 443 if parsed.scheme.casefold() == "https" else 80
    target_port = port or expected_port
    if target_port != expected_port or target_port not in ALLOWED_REMOTE_PORTS:
        raise ValueError("remote article URL must use its standard port 80 or 443")
    try:
        resolver_fn = resolver or socket.getaddrinfo
        addresses = resolver_fn(
            parsed.hostname,
            target_port,
            type=socket.SOCK_STREAM,
        )
    except OSError as ex:
        raise ValueError(f"remote article hostname could not be resolved: {ex}") from ex
    if not addresses:
        raise ValueError("remote article hostname did not resolve")

    resolved: set[ipaddress.IPv4Address | ipaddress.IPv6Address] = set()
    for address in addresses:
        try:
            resolved.add(ipaddress.ip_address(address[4][0]))
        except (IndexError, ValueError) as ex:
            raise ValueError("remote article hostname resolved to an invalid address") from ex
    if not resolved or any(not address.is_global for address in resolved):
        raise ValueError("remote article URL resolves to a non-public network address")
    return url, parsed, tuple(sorted(str(address) for address in resolved))


def _connection_for(parsed, address: str, timeout_s: float):
    port = parsed.port or (443 if parsed.scheme.casefold() == "https" else 80)
    connection_type = (
        _PinnedHTTPSConnection if parsed.scheme.casefold() == "https" else _PinnedHTTPConnection
    )
    return connection_type(parsed.hostname, port, address, timeout_s)


def _open_url(request: Request, timeout_s: float):
    """Open directly to one validated public IP; never resolve again while connecting."""
    url, parsed, addresses = _validated_target(request.full_url)
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    last_error = None
    for address in addresses:
        connection = _connection_for(parsed, address, timeout_s)
        try:
            headers = dict(request.header_items())
            headers.setdefault("Accept-Encoding", "identity")
            connection.request(request.get_method(), path, headers=headers)
            response = connection.getresponse()
        except (OSError, ssl.SSLError, http.client.HTTPException) as ex:
            last_error = ex
            connection.close()
            continue
        if response.status >= 300:
            response_headers = response.headers
            status = response.status
            reason = response.reason
            response.close()
            connection.close()
            raise urllib.error.HTTPError(url, status, reason, response_headers, None)
        return _PinnedResponse(response, connection)
    raise urllib.error.URLError(last_error or "no validated public address was reachable")


def _validate_remote_url(
    url: str,
    *,
    resolver=None,
) -> str:
    """Validate one fetch target and reject non-public network destinations."""
    validated_url, _, _ = _validated_target(url, resolver=resolver)
    return validated_url


def _evidence_url(url: str) -> tuple[str, bool]:
    """Validate URL shape without DNS and remove secret-bearing URL components."""
    if not isinstance(url, str) or not url or len(url) > 4096:
        raise ValueError("remote article URL must be a bounded non-empty string")
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as ex:
        raise ValueError(f"remote article URL is invalid: {ex}") from ex
    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.hostname:
        raise ValueError("remote article URL must use http or https with a hostname")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("remote article URL cannot include credentials")
    if any(ord(character) < 32 or ord(character) == 127 for character in url):
        raise ValueError("remote article URL cannot contain control characters")
    expected_port = 443 if parsed.scheme.casefold() == "https" else 80
    if port not in {None, expected_port}:
        raise ValueError("remote article URL must use its standard port 80 or 443")
    hostname = parsed.hostname.casefold().rstrip(".")
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise ValueError("remote article URL cannot target localhost")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        try:
            hostname.encode("ascii")
        except UnicodeEncodeError as ex:
            raise ValueError("remote article hostname must use ASCII or IDNA form") from ex
    else:
        if not address.is_global:
            raise ValueError("remote article URL cannot target a non-public network address")
    host = f"[{hostname}]" if ":" in hostname else hostname
    netloc = host if port in {None, expected_port} else f"{host}:{port}"
    sanitized = parsed._replace(netloc=netloc, query="", fragment="").geturl()
    return sanitized, sanitized != url


def _sanitize_evidence_link(value: str) -> str:
    if not value.casefold().startswith(("http://", "https://")):
        return value
    try:
        return _evidence_url(value)[0]
    except ValueError:
        return "[REDACTED_URL]"


def is_article_input(value: str) -> bool:
    if video.is_url(value):
        return not VIDEO_HOST_RE.match(value.strip())
    path = Path(value).expanduser()
    if path.suffix.casefold() in SUPPORTED_EXTENSIONS:
        return True
    if path.is_file():
        return _looks_like_feed(path.read_text(encoding="utf-8", errors="replace")[:4096])
    return False


def _looks_like_feed(sample: str) -> bool:
    lowered = sample.lstrip().casefold()
    return lowered.startswith("<?xml") or "<rss" in lowered or "<feed" in lowered


def _local_tag(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text_content(element: ET.Element | None) -> str:
    if element is None:
        return ""
    parts = [element.text or ""]
    for child in element.iter():
        if child is not element:
            parts.append(child.text or "")
            parts.append(child.tail or "")
    return WHITESPACE_RE.sub(" ", "".join(parts)).strip()


def _first_child(parent: ET.Element, names: tuple[str, ...]) -> ET.Element | None:
    for child in parent:
        if _local_tag(child.tag) in names:
            return child
    return None


def _child_text(parent: ET.Element, names: tuple[str, ...]) -> str:
    return _text_content(_first_child(parent, names))


def _parse_feed_xml(text: str) -> dict[str, Any]:
    if re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", text, re.I):
        raise ValueError("feed XML cannot contain document type or entity declarations")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as ex:
        raise ValueError(f"malformed feed XML: {ex}") from ex
    root_name = _local_tag(root.tag)
    if root_name == "rss":
        channel = _first_child(root, ("channel",))
        if channel is None:
            raise ValueError("RSS feed missing channel element")
        feed_title = _child_text(channel, ("title",))
        raw_items = [child for child in channel if _local_tag(child.tag) == "item"]
        entry_kind = "entry"
    elif root_name == "feed":
        feed_title = _child_text(root, ("title",))
        raw_items = [child for child in root if _local_tag(child.tag) == "entry"]
        entry_kind = "entry"
    else:
        raise ValueError("unsupported feed format: expected RSS or Atom")

    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    skipped: list[dict[str, str]] = []
    for raw in raw_items:
        title = _child_text(raw, ("title",))
        link = ""
        for child in raw:
            name = _local_tag(child.tag)
            if name == "link" and child.attrib.get("href") and child.attrib.get("rel", "alternate") == "alternate":
                link = child.attrib["href"]
                break
            if name == "link" and _text_content(child):
                link = _text_content(child)
                break
        id_element = _first_child(raw, ("guid", "id"))
        explicit_id = (id_element.text or "").strip() if id_element is not None else ""
        guid = explicit_id or link
        identity_kind = "id" if explicit_id else "link" if link else "content"
        # Retain distinct query-based identities without persisting URL secrets.
        if guid and _sanitize_evidence_link(guid) != guid:
            guid = "url-sha256:" + hashlib.sha256(guid.encode('utf-8')).hexdigest()
        link = _sanitize_evidence_link(link)
        published = _child_text(raw, ("pubDate", "published", "updated"))
        # Prefer full content even when a summary appears first in document order.
        content = next((element for name in ("encoded", "content", "description", "summary")
                        if (element := _first_child(raw, (name,))) is not None), None)
        body = _text_content(content)
        if content is not None and content.attrib.get("type") == "xhtml":
            body = _html_to_text(ET.tostring(content, encoding="unicode"))
        if content is not None and (_local_tag(content.tag) in {"encoded", "description"} or
                                    content.attrib.get("type") == "html"):
            body = _html_to_text(body)
        if not title and not body:
            skipped.append({"title": guid or "(untitled)", "reason": "empty"})
            continue
        if not guid:
            # Missing IDs cannot make unrelated entries with the same title vanish.
            guid = hashlib.sha256(json.dumps([title, published, body], ensure_ascii=False).encode()).hexdigest()
        dedupe_key = guid
        if dedupe_key in seen:
            skipped.append({"title": title or guid, "reason": "duplicate"})
            continue
        seen.add(dedupe_key)
        entries.append({
            "title": title or "(untitled)",
            "link": link,
            "published": published,
            "guid": guid,
            "identity_kind": identity_kind,
            "body": body,
            "author": _child_text(raw, ("author", "creator")) or None,
            "content_kind": _local_tag(content.tag) if content is not None else "missing",
            "enclosures": [
                {"url": _sanitize_evidence_link(child.attrib.get("url") or child.attrib.get("href", "")),
                 "type": child.attrib.get("type", "")}
                for child in raw if _local_tag(child.tag) == "enclosure" or
                (_local_tag(child.tag) == "link" and child.attrib.get("rel") == "enclosure")
            ],
            "word_count": _word_count(body or title),
        })
    if not entries and not raw_items:
        raise ValueError("feed contains no entries")
    return {
        "kind": "feed",
        "feed_title": feed_title or "(untitled feed)",
        "entry_kind": entry_kind,
        "entries": entries,
        "skipped": skipped,
    }


def _word_count(text: str) -> int:
    return len(WHITESPACE_RE.sub(" ", text.strip()).split()) if text.strip() else 0


def _html_to_text(content: str) -> str:
    without_blocks = SCRIPT_STYLE_RE.sub(" ", content)
    unescaped = html.unescape(without_blocks)
    stripped = TAG_RE.sub(" ", unescaped)
    return WHITESPACE_RE.sub(" ", stripped).strip()


def _read_document(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    suffix = path.suffix.casefold()
    if suffix in FEED_EXTENSIONS or _looks_like_feed(text[:4096]):
        parsed = _parse_feed_xml(text)
        parsed["input"] = str(path.resolve())
        parsed["source"] = "local"
        return parsed
    if suffix in {".html", ".htm"}:
        body = _html_to_text(text)
        title = _extract_html_title(text) or path.stem
    elif suffix in {".md", ".markdown"}:
        body = text.strip()
        title = _extract_markdown_title(body) or path.stem
    else:
        body = text.strip()
        title = path.stem
    if not body:
        raise ValueError(f"document is empty: {path.name}")
    return {
        "kind": "article",
        "source": "local",
        "input": str(path.resolve()),
        "title": title,
        "body": body,
        "word_count": _word_count(body),
        "entries": [{
            "title": title,
            "body": body,
            "word_count": _word_count(body),
            "link": "",
            "published": "",
            "guid": str(path.resolve()),
        }],
        "entry_kind": "article",
        "skipped": [],
    }


def _extract_html_title(content: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", content, re.I | re.DOTALL)
    return WHITESPACE_RE.sub(" ", html.unescape(match.group(1))).strip() if match else ""


def _extract_markdown_title(content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return ""


def _url_probe(inp: str) -> dict[str, Any]:
    display_input, input_redacted = _evidence_url(inp)
    return {
        "source": "url",
        "input": display_input,
        "input_redacted": input_redacted,
        "kind": "article_url",
        "entry_kind": "article",
        "availability": "remote_fetch_required",
        "requires_fetch_approval": True,
        "requires_browser_auth": False,
        "browser_auth_note": (
            "Paywalled or subscriber content may require browser-assisted reading; "
            "CLI never reads browser credentials."
        ),
        "item_count": 1,
        "estimated_words": DEFAULT_URL_WORDS,
        "entries": [{
            "index": 1,
            "title": display_input,
            "link": display_input,
            "published": "",
            "word_count": DEFAULT_URL_WORDS,
            "availability": "not_fetched",
        }],
        "skipped": [],
    }


def _fetch_url(url: str, timeout_s: float = 20.0) -> str:
    current_url = url
    for redirect_count in range(MAX_REDIRECTS + 1):
        current_url = _validate_remote_url(current_url)
        request = Request(
            current_url,
            headers={
                "Accept": "text/html, text/plain, application/rss+xml, application/atom+xml, application/xml;q=0.9",
                "User-Agent": "Voidscape/1.0 article-reader",
            },
        )
        try:
            response = _open_url(request, timeout_s)
        except urllib.error.HTTPError as ex:
            if ex.code in {301, 302, 303, 307, 308}:
                location = ex.headers.get("Location", "")
                if not location:
                    raise RuntimeError("network fetch failed: redirect missing Location") from ex
                if redirect_count >= MAX_REDIRECTS:
                    raise RuntimeError("network fetch failed: too many redirects") from ex
                next_url = urljoin(current_url, location)
                if (
                    urlsplit(current_url).scheme.casefold() == "https"
                    and urlsplit(next_url).scheme.casefold() == "http"
                ):
                    raise RuntimeError("network fetch failed: HTTPS redirect downgrade refused") from ex
                current_url = next_url
                continue
            if ex.code in (401, 403):
                raise PermissionError(
                    "remote article may require authenticated browser access; "
                    "CLI fetch cannot use browser credentials"
                ) from ex
            raise RuntimeError(f"network fetch failed: HTTP {ex.code}") from ex
        except urllib.error.URLError as ex:
            raise RuntimeError(f"network fetch failed: {ex.reason}") from ex

        with response:
            content_type = response.headers.get("Content-Type", "")
            media_type = content_type.split(";", 1)[0].strip().casefold()
            if not media_type or media_type not in REMOTE_CONTENT_TYPES:
                raise ValueError(
                    f"remote article returned unsupported content type: {media_type or '(missing)'}"
                )
            content_encoding = response.headers.get("Content-Encoding", "").strip().casefold()
            if content_encoding not in {"", "identity"}:
                raise ValueError("remote article returned unsupported content encoding")
            charset = "utf-8"
            if "charset=" in content_type.casefold():
                charset = (
                    content_type.casefold().split("charset=", 1)[1].split(";", 1)[0]
                    .strip().strip("\"'")
                )
            payload = bytearray()
            while True:
                chunk = response.read(min(65536, MAX_REMOTE_BYTES + 1 - len(payload)))
                if not chunk:
                    break
                payload.extend(chunk)
                if len(payload) > MAX_REMOTE_BYTES:
                    raise ValueError(
                        f"remote article exceeds the {MAX_REMOTE_BYTES}-byte response limit"
                    )
            try:
                return payload.decode(charset, errors="replace")
            except LookupError as ex:
                raise ValueError(f"remote article declared unsupported charset: {charset}") from ex
    raise RuntimeError("network fetch failed: too many redirects")


def _read_url(url: str) -> dict[str, Any]:
    content = _fetch_url(url)
    display_url, input_redacted = _evidence_url(url)
    if _looks_like_feed(content[:4096]):
        parsed = _parse_feed_xml(content)
        parsed["input"] = display_url
        parsed["input_redacted"] = input_redacted
        parsed["source"] = "url"
        return parsed
    body = _html_to_text(content)
    if not body:
        raise ValueError("unsupported or empty remote content")
    title = _extract_html_title(content) or display_url
    return {
        "kind": "article",
        "source": "url",
        "input": display_url,
        "input_redacted": input_redacted,
        "title": title,
        "body": body,
        "word_count": _word_count(body),
        "entries": [{
            "title": title,
            "body": body,
            "word_count": _word_count(body),
            "link": display_url,
            "published": "",
            "guid": display_url,
        }],
        "entry_kind": "article",
        "skipped": [],
    }


def _ordered_entries(info: dict[str, Any]) -> list[dict[str, Any]]:
    entries = list(info.get("entries") or [])
    ordered = []
    for index, entry in enumerate(entries, start=1):
        ordered.append({
            "index": index,
            "citation": f"[{info.get('entry_kind', 'entry')} {index}]",
            "title": entry.get("title") or "(untitled)",
            "link": entry.get("link", ""),
            "published": entry.get("published", ""),
            "guid": entry.get("guid", ""),
            "word_count": entry.get("word_count", _word_count(entry.get("body", ""))),
            "body": entry.get("body", ""),
        })
    return ordered


def probe(inp: str) -> dict[str, Any]:
    resolved = video.resolve_input(inp)
    if video.is_url(resolved):
        return _url_probe(resolved)
    path = Path(resolved).expanduser()
    if not path.exists():
        raise FileNotFoundError(video.describe_missing_input(resolved))
    if path.is_symlink():
        raise ValueError(f"article input cannot be a symlink: {resolved}")
    if not path.is_file():
        raise ValueError(f"article input is not a file: {resolved}")
    info = _read_document(path)
    entries = _ordered_entries(info)
    return {
        "source": info["source"],
        "input": info["input"],
        "kind": info["kind"],
        "feed_title": info.get("feed_title"),
        "entry_kind": info["entry_kind"],
        "item_count": len(entries),
        "within_limit": len(entries) <= MAX_ENTRIES,
        "entries": [{
            "index": item["index"],
            "title": item["title"],
            "link": item["link"],
            "published": item["published"],
            "word_count": item["word_count"],
            "citation": item["citation"],
        } for item in entries],
        "skipped": info.get("skipped", []),
        "requires_fetch_approval": False,
        "requires_browser_auth": False,
    }


def estimate(inp: str, out_words: int = 600,
             agent_model: str | None = None) -> dict[str, Any]:
    if out_words < 0:
        raise ValueError("out_words cannot be negative")
    info = probe(inp)
    if info["item_count"] > MAX_ENTRIES:
        raise ValueError("feed has more than 100 entries; choose a narrower source")

    pricing = video.load_pricing()
    selected_model, model_rate, _estimator = video._agent_rate(pricing, agent_model)
    if info["source"] == "url":
        text_words = info.get("estimated_words", DEFAULT_URL_WORDS)
    else:
        text_words = sum(item["word_count"] for item in info["entries"])
    text_tokens = round(text_words * 1.33)
    output_tokens = round(out_words * 1.33)
    overhead_tokens = 2000
    read_tokens = text_tokens + overhead_tokens
    agent_usd = round(
        read_tokens / 1e6 * model_rate["input"]
        + output_tokens / 1e6 * model_rate["output"],
        4,
    )
    drivers_usd = {
        "text": text_tokens / 1e6 * model_rate["input"],
        "overhead": overhead_tokens / 1e6 * model_rate["input"],
        "output": output_tokens / 1e6 * model_rate["output"],
    }
    requires_fetch = info["source"] == "url"
    return {
        "input": info["input"],
        "input_redacted": bool(info.get("input_redacted", False)),
        "source": info["source"],
        "kind": info["kind"],
        "entry_kind": info["entry_kind"],
        "item_count": info["item_count"],
        "entries": info["entries"],
        "skipped": info.get("skipped", []),
        "tokens": {
            "text": text_tokens,
            "output": output_tokens,
            "overhead": overhead_tokens,
            "read_total": read_tokens,
        },
        "cost_usd": {"transcription": 0.0, "agent": agent_usd, "total": agent_usd},
        "dominant_cost": max(drivers_usd, key=drivers_usd.get),
        "free": not requires_fetch,
        "needs_install": False,
        "requires_cloud_approval": requires_fetch,
        "gate": {"type": "cloud_approval", "backend": "article_fetch"} if requires_fetch else None,
        "requires_fetch_approval": requires_fetch,
        "requires_browser_auth": False,
        "browser_auth_note": (
            "Paywalled or subscriber content may require browser-assisted reading; "
            "CLI never reads browser credentials."
        ),
        "needs_model_download": False,
        "model_download": {"status": "not_applicable", "model": None},
        "agent_model": selected_model,
        "cost_basis": (
            "API-equivalent estimate; Codex subscription usage may not be billed per API token"
            if selected_model.startswith("gpt-5.6-") else "API token estimate"
        ),
    }


def run(inp: str, workdir: str | None = None, *,
        allow_fetch: bool = False) -> dict[str, Any]:
    return video.execute_read(_run, inp, workdir, allow_fetch=allow_fetch)


def _run(progress, inp, workdir, *, allow_fetch):
    resolved = video.resolve_input(inp)
    if video.is_url(resolved):
        if not allow_fetch:
            raise video.ApprovalRequired(
                "remote article fetch needs explicit consent; review preview, "
                "then rerun with --allow-fetch", "cloud_approval", "article_fetch"
            )
        info = progress.call("fetch", _read_url, resolved)
    else:
        path = Path(resolved).expanduser()
        if not path.exists():
            raise FileNotFoundError(video.describe_missing_input(resolved))
        if path.is_symlink():
            raise ValueError(f"article input cannot be a symlink: {resolved}")
        if not path.is_file():
            raise ValueError(f"article input is not a file: {resolved}")
        info = progress.call("probe", _read_document, path)

    progress.begin("validate")
    entries = _ordered_entries(info)
    if len(entries) > MAX_ENTRIES:
        raise ValueError("feed has more than 100 entries; choose a narrower source")

    progress.complete("validate")
    progress.begin("workdir")
    destination = Path(workdir).expanduser() if workdir else Path(
        tempfile.mkdtemp(prefix="voidscape-articles-")
    )
    if destination.is_symlink():
        raise ValueError(f"workdir cannot be a symlink: {destination}")
    if destination.exists():
        if not destination.is_dir() or any(destination.iterdir()):
            raise ValueError(f"workdir already exists and is not empty: {destination}")
    try:
        entries_dir = destination / "entries"
        entries_dir.mkdir(parents=True, exist_ok=True)
    except OSError as ex:
        raise RuntimeError(f"workdir creation failed: {ex}") from ex
    progress.complete("workdir")

    written = []
    result = {
        "workdir": str(destination.resolve()),
        "kind": info["kind"], "source": info["source"], "input": info["input"],
        "input_redacted": bool(info.get("input_redacted", False)),
        "feed_title": info.get("feed_title"), "entry_kind": info["entry_kind"],
        "item_count": len(entries), "entries": written, "skipped": info.get("skipped", []),
        "content_trust": video.EVIDENCE_TRUST.copy(),
        "citation_guide": f"cite each excerpt with {info['entry_kind']} N, e.g. [{info['entry_kind']} 1]",
    }
    progress.result = result
    progress.begin("write_entries")
    for item in entries:
        slug = (re.sub(r"[^A-Za-z0-9._-]+", "-", item["title"]).strip("-") or "entry")[:80]
        target = entries_dir / f"{item['index']:03d}-{slug}.txt"
        header = [
            f"title: {item['title']}",
            f"citation: {item['citation']}",
        ]
        if item["link"]:
            header.append(f"link: {item['link']}")
        if item["published"]:
            header.append(f"published: {item['published']}")
        body = "\n".join(header) + "\n\n" + (item["body"] or "")
        try:
            target.write_text(body, encoding="utf-8")
        except OSError as ex:
            raise RuntimeError(f"entry write failed: {ex}") from ex
        written.append({
            "index": item["index"],
            "citation": item["citation"],
            "file": str(target.resolve()),
            "title": item["title"],
            "link": item["link"],
            "published": item["published"],
            "word_count": item["word_count"],
        })

    progress.complete("write_entries")
    return progress.finish(result, wrap_manifest_errors=True)


def _cli_manifest() -> dict[str, Any]:
    common = ["--human", "--envelope", "--compact"]
    return {
        "protocol_version": "1.0",
        "interactive": False,
        "commands": {
            "manifest": {"description": "describe the article CLI contract", "flags": common},
            "probe": {"description": "inspect a local article or feed", "flags": common},
            "estimate": {
                "description": "price text tokens before copying evidence",
                "flags": ["--out-words", "--agent-model", *common],
            },
            "run": {
                "description": "copy ordered entries and write a manifest",
                "flags": ["--workdir", "--allow-fetch", *common],
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
    lines = [
        f"input: {result['input']}  ({result['kind']}, {result['item_count']} items)",
        f"agent={result['agent_model']}",
        f"  text tokens:   {tokens['text']:>8}",
        f"  output tokens: {tokens['output']:>8}",
        "  ---",
        f"  agent tokens: ${cost['agent']:.4f}",
        f"  TOTAL:        ${cost['total']:.4f}   (dominant: {result['dominant_cost']})",
        f"  basis: {result['cost_basis']}",
    ]
    if result.get("requires_fetch_approval"):
        lines.append("  fetch: remote URL requires explicit --allow-fetch approval")
    return "\n".join(lines)


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
        prog="article.py", description="local article and RSS/Atom evidence engine",
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
    run_parser.add_argument("--allow-fetch", action="store_true")
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
            result = run(args.input, args.workdir, allow_fetch=args.allow_fetch)
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
