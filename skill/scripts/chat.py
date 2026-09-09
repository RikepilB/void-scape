"""Local chat export (WhatsApp-style .txt) evidence engine."""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

if __package__:
    from . import video
else:
    import video


CHAT_EXTENSION = ".txt"
MAX_MESSAGES = 2000
DETECT_SCAN_LINES = 40
ENCRYPTION_NOTICE = "Messages and calls are end-to-end encrypted"
HEADER_RE = re.compile(r"^\[(?P<stamp>[^\]]{4,40})\]\s?(?P<rest>.*)$")
ATTACHED_RE = re.compile(r"<attached:\s*(?P<name>[^<>]+)>")
OMITTED_RE = re.compile(
    r"(?P<name>[\w .()-]+\.(?:jpe?g|png|webp|gif|mp4|m4v|mov|mp3|m4a|opus|ogg|wav|pdf|"
    r"docx?|xlsx?|pptx?|csv|zip|vcf))\s+omitted",
    re.I,
)


def looks_like_chat_export(text: str) -> bool:
    """True when the sample reads like a WhatsApp-style timestamped export."""
    seen = 0
    for line in text.splitlines():
        if not line.strip():
            continue
        if HEADER_RE.match(line):
            seen += 1
            if seen >= 2:
                return True
        if seen == 0 and ENCRYPTION_NOTICE in line:
            return True
    return False


def is_chat_input(value: str) -> bool:
    if video.is_url(value):
        return False
    path = Path(video.resolve_input(value)).expanduser()
    if path.suffix.casefold() != CHAT_EXTENSION or not path.is_file():
        return False
    try:
        sample = path.read_text(encoding="utf-8", errors="replace")[:8192]
    except OSError:
        return False
    return looks_like_chat_export(sample)


def _detect_scan(text: str) -> bool:
    lines = [line for line in text.splitlines() if line.strip()][:DETECT_SCAN_LINES]
    return looks_like_chat_export("\n".join(lines))


def _split_sender(rest: str) -> tuple[str | None, str]:
    if ": " in rest:
        sender, body = rest.split(": ", 1)
        if sender.strip() and not HEADER_RE.match(sender):
            return sender.strip(), body
    return None, rest


def _media_name(text: str) -> str | None:
    attached = ATTACHED_RE.search(text)
    if attached:
        return attached.group("name").strip()
    omitted = OMITTED_RE.search(text)
    if omitted:
        return omitted.group("name").strip()
    return None


def _word_count(text: str) -> int:
    return len(text.split()) if text.strip() else 0


def _resolve_media(name: str | None, source: Path) -> str | None:
    if not name:
        return None
    candidate = source.parent / name
    return str(candidate.resolve()) if candidate.is_file() else None


def _parse_export(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        raise ValueError(f"chat export is empty: {path.name}")
    if not _detect_scan(text):
        raise ValueError(
            "file is not a recognized chat export; expected WhatsApp-style "
            "'[timestamp] sender: message' lines"
        )

    raw: list[dict[str, Any]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        match = HEADER_RE.match(line)
        if match:
            sender, body = _split_sender(match.group("rest"))
            media = _media_name(body)
            raw.append({
                "stamp": match.group("stamp").strip(),
                "sender": sender,
                "text": "" if media else body.strip(),
                "media": media,
                "kind": "system" if sender is None else ("media" if media else "text"),
            })
        elif raw:
            raw[-1]["text"] = (raw[-1]["text"] + "\n" + line.rstrip()).strip()

    if not raw:
        raise ValueError("chat export contains no timestamped messages")

    entries = []
    for index, message in enumerate(raw[:MAX_MESSAGES], start=1):
        entries.append({
            "index": index,
            "citation": f"[message {index}]",
            "stamp": message["stamp"],
            "sender": message["sender"] or "",
            "kind": message["kind"],
            "text": message["text"],
            "media": message["media"],
            "media_file": _resolve_media(message["media"], path),
            "word_count": _word_count(message["text"]),
        })

    participants = sorted({
        entry["sender"] for entry in entries if entry["sender"]
    })
    return {
        "kind": "chat",
        "source": "local",
        "input": str(path.resolve()),
        "chat_title": _chat_title(path),
        "entry_kind": "message",
        "entries": entries,
        "truncated": len(raw) > MAX_MESSAGES,
        "raw_message_count": len(raw),
        "participants": participants,
        "kind_counts": {
            kind: sum(1 for entry in entries if entry["kind"] == kind)
            for kind in ("text", "media", "system")
        },
    }


def _chat_title(path: Path) -> str:
    if path.stem.casefold() == "_chat":
        return path.parent.name or path.stem
    return path.stem


def probe(inp: str) -> dict[str, Any]:
    resolved = video.resolve_input(inp)
    if video.is_url(resolved):
        raise ValueError("chat exports are local files; a URL is not a chat export")
    path = Path(resolved).expanduser()
    if not path.exists():
        raise FileNotFoundError(video.describe_missing_input(resolved))
    if path.is_symlink():
        raise ValueError(f"chat input cannot be a symlink: {resolved}")
    if not path.is_file():
        raise ValueError(f"chat input is not a file: {resolved}")
    info = _parse_export(path)
    return {
        "source": info["source"],
        "input": info["input"],
        "kind": info["kind"],
        "chat_title": info["chat_title"],
        "entry_kind": info["entry_kind"],
        "item_count": len(info["entries"]),
        "within_limit": not info["truncated"],
        "raw_message_count": info["raw_message_count"],
        "truncated": info["truncated"],
        "participants": info["participants"],
        "kind_counts": info["kind_counts"],
        "entries": [{
            "index": entry["index"],
            "citation": entry["citation"],
            "sender": entry["sender"],
            "stamp": entry["stamp"],
            "kind": entry["kind"],
            "word_count": entry["word_count"],
            "media": entry["media"],
        } for entry in info["entries"]],
        "requires_cloud_approval": False,
        "needs_model_download": False,
    }


def estimate(inp: str, out_words: int = 600,
             agent_model: str | None = None) -> dict[str, Any]:
    if out_words < 0:
        raise ValueError("out_words cannot be negative")
    info = _parse_export(Path(video.resolve_input(inp)).expanduser())
    if info["truncated"]:
        raise ValueError(
            f"chat export has more than {MAX_MESSAGES} messages; export a narrower window"
        )

    pricing = video.load_pricing()
    selected_model, model_rate, _estimator = video._agent_rate(pricing, agent_model)
    text_words = sum(entry["word_count"] for entry in info["entries"])
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
    return {
        "input": info["input"],
        "input_redacted": False,
        "source": info["source"],
        "kind": info["kind"],
        "chat_title": info["chat_title"],
        "entry_kind": info["entry_kind"],
        "item_count": len(info["entries"]),
        "participants": info["participants"],
        "kind_counts": info["kind_counts"],
        "entries": [{
            "index": entry["index"],
            "citation": entry["citation"],
            "sender": entry["sender"],
            "kind": entry["kind"],
            "word_count": entry["word_count"],
        } for entry in info["entries"]],
        "tokens": {
            "text": text_tokens,
            "output": output_tokens,
            "overhead": overhead_tokens,
            "read_total": read_tokens,
        },
        "cost_usd": {"transcription": 0.0, "agent": agent_usd, "total": agent_usd},
        "dominant_cost": max(drivers_usd, key=drivers_usd.get),
        "free": True,
        "needs_install": False,
        "requires_cloud_approval": False,
        "requires_browser_auth": False,
        "needs_model_download": False,
        "model_download": {"status": "not_applicable", "model": None},
        "agent_model": selected_model,
        "cost_basis": (
            "API-equivalent estimate; Codex subscription usage may not be billed per API token"
            if selected_model.startswith("gpt-5.6-") else "API token estimate"
        ),
    }


def run(inp: str, workdir: str | None = None) -> dict[str, Any]:
    resolved = video.resolve_input(inp)
    if video.is_url(resolved):
        raise ValueError("chat exports are local files; a URL is not a chat export")
    path = Path(resolved).expanduser()
    if not path.exists():
        raise FileNotFoundError(video.describe_missing_input(resolved))
    if path.is_symlink():
        raise ValueError(f"chat input cannot be a symlink: {resolved}")
    if not path.is_file():
        raise ValueError(f"chat input is not a file: {resolved}")
    info = _parse_export(path)
    if info["truncated"]:
        raise ValueError(
            f"chat export has more than {MAX_MESSAGES} messages; export a narrower window"
        )

    destination = Path(workdir).expanduser() if workdir else Path(
        tempfile.mkdtemp(prefix="voidscape-chat-")
    )
    if destination.is_symlink():
        raise ValueError(f"workdir cannot be a symlink: {destination}")
    if destination.exists():
        if not destination.is_dir() or any(destination.iterdir()):
            raise ValueError(f"workdir already exists and is not empty: {destination}")
    try:
        destination.mkdir(parents=True, exist_ok=True)
    except OSError as ex:
        raise RuntimeError(f"workdir creation failed: {ex}") from ex

    transcript_lines = [
        f"chat: {info['chat_title']}",
        f"source: {info['input']}",
        f"messages: {len(info['entries'])}",
        "",
    ]
    for entry in info["entries"]:
        header = f"{entry['citation']} {entry['sender'] or 'system'} · {entry['stamp']}"
        transcript_lines.append(header)
        if entry["media"]:
            media_note = f"[media: {entry['media']}"
            if entry["media_file"]:
                media_note += f" · file: {entry['media_file']}"
            transcript_lines.append(media_note + "]")
        if entry["text"]:
            transcript_lines.append(entry["text"])
        transcript_lines.append("")
    transcript_path = destination / "messages.txt"
    try:
        transcript_path.write_text(
            "\n".join(transcript_lines).rstrip() + "\n", encoding="utf-8"
        )
    except OSError as ex:
        raise RuntimeError(f"transcript write failed: {ex}") from ex

    result = {
        "workdir": str(destination.resolve()),
        "kind": info["kind"],
        "source": info["source"],
        "input": info["input"],
        "chat_title": info["chat_title"],
        "entry_kind": info["entry_kind"],
        "item_count": len(info["entries"]),
        "participants": info["participants"],
        "kind_counts": info["kind_counts"],
        "transcript": str(transcript_path.resolve()),
        "entries": [{
            "index": entry["index"],
            "citation": entry["citation"],
            "sender": entry["sender"],
            "stamp": entry["stamp"],
            "kind": entry["kind"],
            "word_count": entry["word_count"],
            "media": entry["media"],
            "media_file": entry["media_file"],
        } for entry in info["entries"]],
        "content_trust": video.EVIDENCE_TRUST.copy(),
        "citation_guide": "cite each excerpt with message N, e.g. [message 1]",
    }
    try:
        (destination / "manifest.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as ex:
        raise RuntimeError(f"manifest write failed: {ex}") from ex
    video.write_read_pointer(result)
    return result


def _cli_manifest() -> dict[str, Any]:
    common = ["--human", "--envelope", "--compact"]
    return {
        "protocol_version": "1.0",
        "interactive": False,
        "commands": {
            "manifest": {"description": "describe the chat CLI contract", "flags": common},
            "probe": {"description": "inspect a local chat export", "flags": common},
            "estimate": {
                "description": "price text tokens before copying evidence",
                "flags": ["--out-words", "--agent-model", *common],
            },
            "run": {
                "description": "write the ordered transcript and a manifest",
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
    lines = [
        f"input: {result['input']}  ({result['kind']}, {result['item_count']} messages)",
        f"chat: {result['chat_title']} · participants: {', '.join(result['participants']) or 'unknown'}",
        f"agent={result['agent_model']}",
        f"  text tokens:   {tokens['text']:>8}",
        f"  output tokens: {tokens['output']:>8}",
        "  ---",
        f"  agent tokens: ${cost['agent']:.4f}",
        f"  TOTAL:        ${cost['total']:.4f}   (dominant: {result['dominant_cost']})",
        f"  basis: {result['cost_basis']}",
        "  privacy: local file only · nothing leaves the machine",
    ]
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
        prog="chat.py", description="local chat export evidence engine",
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
            error = video._error_payload(ex)
            print(video._json_text(video._envelope(None, error, args.command), args.compact))
        else:
            print(video._json_text({"error": str(ex)}, args.compact))
        return exit_code
    return 0


if __name__ == "__main__":
    sys.exit(main())
