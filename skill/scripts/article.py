"""Local article, HTML, Markdown, and RSS/Atom evidence engine."""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
import tempfile
import urllib.error
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

import video


ARTICLE_EXTENSIONS = {".html", ".htm", ".md", ".markdown", ".txt"}
FEED_EXTENSIONS = {".xml", ".rss", ".atom"}
SUPPORTED_EXTENSIONS = ARTICLE_EXTENSIONS | FEED_EXTENSIONS
MAX_ENTRIES = 100
DEFAULT_URL_WORDS = 1200
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
            if name == "link" and child.attrib.get("href"):
                link = child.attrib["href"]
                break
            if name == "link" and _text_content(child):
                link = _text_content(child)
                break
        guid = _child_text(raw, ("guid", "id")) or link or title
        published = _child_text(raw, ("pubDate", "published", "updated"))
        body = _child_text(raw, ("content:encoded", "content", "description", "summary"))
        if not title and not body:
            skipped.append({"title": guid or "(untitled)", "reason": "empty"})
            continue
        dedupe_key = guid or link or f"{title}|{published}"
        if dedupe_key in seen:
            skipped.append({"title": title or guid, "reason": "duplicate"})
            continue
        seen.add(dedupe_key)
        entries.append({
            "title": title or "(untitled)",
            "link": link,
            "published": published,
            "guid": guid,
            "body": body,
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
    return {
        "source": "url",
        "input": inp,
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
            "title": inp,
            "link": inp,
            "published": "",
            "word_count": DEFAULT_URL_WORDS,
            "availability": "not_fetched",
        }],
        "skipped": [],
    }


def _fetch_url(url: str, timeout_s: float = 20.0) -> str:
    request = Request(url, headers={"User-Agent": "Voidscape/1.0 article-reader"})
    try:
        with urlopen(request, timeout=timeout_s) as response:
            content_type = response.headers.get("Content-Type", "")
            charset = "utf-8"
            if "charset=" in content_type.lower():
                charset = content_type.lower().split("charset=", 1)[1].split(";", 1)[0].strip()
            return response.read().decode(charset, errors="replace")
    except urllib.error.HTTPError as ex:
        if ex.code in (401, 403):
            raise PermissionError(
                "remote article may require authenticated browser access; "
                "CLI fetch cannot use browser credentials"
            ) from ex
        raise RuntimeError(f"network fetch failed: HTTP {ex.code}") from ex
    except urllib.error.URLError as ex:
        raise RuntimeError(f"network fetch failed: {ex.reason}") from ex


def _read_url(url: str) -> dict[str, Any]:
    content = _fetch_url(url)
    if _looks_like_feed(content[:4096]):
        parsed = _parse_feed_xml(content)
        parsed["input"] = url
        parsed["source"] = "url"
        return parsed
    body = _html_to_text(content)
    if not body:
        raise ValueError("unsupported or empty remote content")
    title = _extract_html_title(content) or url
    return {
        "kind": "article",
        "source": "url",
        "input": url,
        "title": title,
        "body": body,
        "word_count": _word_count(body),
        "entries": [{
            "title": title,
            "body": body,
            "word_count": _word_count(body),
            "link": url,
            "published": "",
            "guid": url,
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
        raise FileNotFoundError(f"no such file: {resolved}")
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
    resolved = video.resolve_input(inp)
    if video.is_url(resolved):
        if not allow_fetch:
            raise PermissionError(
                "remote article fetch needs explicit consent; review preview, "
                "then rerun with --allow-fetch"
            )
        info = _read_url(resolved)
    else:
        path = Path(resolved).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"no such file: {resolved}")
        info = _read_document(path)

    entries = _ordered_entries(info)
    if len(entries) > MAX_ENTRIES:
        raise ValueError("feed has more than 100 entries; choose a narrower source")

    destination = Path(workdir).expanduser() if workdir else Path(
        tempfile.mkdtemp(prefix="voidscape-articles-")
    )
    if destination.exists():
        if not destination.is_dir() or any(destination.iterdir()):
            raise ValueError(f"workdir already exists and is not empty: {destination}")
    try:
        entries_dir = destination / "entries"
        entries_dir.mkdir(parents=True, exist_ok=True)
    except OSError as ex:
        raise RuntimeError(f"workdir creation failed: {ex}") from ex

    written = []
    for item in entries:
        slug = re.sub(r"[^A-Za-z0-9._-]+", "-", item["title"]).strip("-") or "entry"
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

    result = {
        "workdir": str(destination.resolve()),
        "kind": info["kind"],
        "source": info["source"],
        "input": info["input"],
        "feed_title": info.get("feed_title"),
        "entry_kind": info["entry_kind"],
        "item_count": len(written),
        "entries": written,
        "skipped": info.get("skipped", []),
        "citation_guide": (
            f"cite each excerpt with {info['entry_kind']} N, e.g. "
            f"[{info['entry_kind']} 1]"
        ),
    }
    try:
        (destination / "manifest.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as ex:
        raise RuntimeError(f"manifest write failed: {ex}") from ex
    return result


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


def _emit(obj: dict[str, Any], human: bool, envelope: bool,
          compact: bool, command: str) -> None:
    if human and "cost_usd" in obj:
        print(_fmt_estimate(obj))
        return
    payload = video._envelope(obj, None, command) if envelope else obj
    print(video._json_text(payload, compact))


def _add_output_modes(parser: argparse.ArgumentParser) -> None:
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--human", action="store_true")
    modes.add_argument("--envelope", action="store_true")
    parser.add_argument("--compact", action="store_true")


def main(argv: list[str] | None = None) -> int:
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
        _emit(result, args.human, args.envelope, args.compact, args.command)
    except Exception as ex:
        exit_code, code, retryable = video._classify_error(ex)
        if args.envelope:
            error = {
                "code": code, "message": str(ex),
                "retryable": retryable, "exit_code": exit_code,
            }
            print(video._json_text(video._envelope(None, error, args.command), args.compact))
        else:
            print(video._json_text({"error": str(ex)}, args.compact))
        return exit_code
    return 0


if __name__ == "__main__":
    sys.exit(main())
