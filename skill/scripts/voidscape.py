"""Voidscape's guided, human-friendly front door for the stable read-video engine."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

import video


WELCOME = r"""
__     ______  ________  _____ _________    ____  ______
\ \   / / __ \/  _/ __ \/ ___// ____/   |  / __ \/ ____/
 \ \ / / / / // // / / /\__ \,< / /   / /| | / /_/ / __/
  \ V / /_/ // // /_/ /___/ / /| |/ /___ |/ ____/ /___
   \_/ \____/___/_____/____/_/ |_|____/_/ |_/_/   /_____/

VOIDSCAPE — LOCAL-FIRST MEDIA WORKFLOW

Your private media, made legible.

  inspect <file-or-url>   See what is there and choose a scope.
  preview <file-or-url>   See cost, privacy, and dependencies.
  read <file-or-url>      Create approved frames, transcript, and manifest.

  customize               Choose local folders and defaults.
  doctor                  Check local readiness without changing anything.

Start here:
  voidscape.py inspect "meeting.mp4"

Agent workflow:
  /voidscape <file-or-url>
""".strip()


SKILL_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_PATH = SKILL_ROOT / "workspace.json"


def _workspace_path(config: str | None = None) -> Path:
    if config:
        return Path(config).expanduser()
    configured = os.environ.get("VOIDSCAPE_WORKSPACE_PATH")
    return Path(configured).expanduser() if configured else WORKSPACE_PATH


def _load_workspace(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _defaults(workspace: dict[str, Any]) -> dict[str, Any]:
    return {
        "tier": workspace.get("default_tier", "both"),
        "backend": workspace.get("default_backend", "captions"),
        "agent_model": workspace.get("agent_model"),
        "whisper_model": workspace.get("whisper_model", "small"),
        "threshold": workspace.get("transcription_thorough_threshold_s", 45),
    }


def _emit(data: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, indent=2, ensure_ascii=False))


def _duration(seconds: float | None) -> str:
    if not seconds:
        return "unknown duration"
    minutes, remainder = divmod(round(seconds), 60)
    return f"{minutes}m {remainder:02d}s" if minutes else f"{remainder}s"


def _recommend_tier(info: dict[str, Any]) -> str:
    if not info.get("has_audio"):
        return "visual"
    if info.get("sidecar_transcript") or info.get("captions_available"):
        return "both"
    return "both"


def _print_error(ex: Exception, as_json: bool) -> int:
    exit_code, code, retryable = video._classify_error(ex)
    if as_json:
        print(json.dumps({"ok": False, "error": {"code": code, "message": str(ex),
                                                  "retryable": retryable,
                                                  "exit_code": exit_code}},
                         indent=2, ensure_ascii=False))
    else:
        print(f"Voidscape could not continue: {ex}", file=sys.stderr)
    return exit_code


def inspect_source(args: argparse.Namespace) -> int:
    try:
        info = video.probe(args.input)
    except Exception as ex:
        return _print_error(ex, args.json)
    if args.json:
        _emit(info, True)
        return 0
    source = "web link" if info.get("source") == "url" else "local file"
    print("Voidscape inspection")
    print(f"  Source: {source} · {_duration(info.get('duration_s'))}")
    print(f"  Video: {info.get('width') or '?'}×{info.get('height') or '?'}")
    print(f"  Audio: {'available' if info.get('has_audio') else 'not detected'}")
    transcript = "sidecar transcript" if info.get("sidecar_transcript") else (
        "captions may be available" if info.get("captions_available") else "no transcript found")
    print(f"  Text: {transcript}")
    print(f"  Suggested scope: {_recommend_tier(info)}")
    print(f"Next: voidscape.py preview {args.input!r}")
    return 0


def _estimate_from_args(args: argparse.Namespace, workspace: dict[str, Any]) -> dict[str, Any]:
    defaults = _defaults(workspace)
    return video.estimate(
        args.input,
        getattr(args, "frames", None),
        getattr(args, "backend", None) or defaults["backend"],
        getattr(args, "out_words", 600),
        getattr(args, "tier", None) or defaults["tier"],
        transcribe_mode=getattr(args, "transcribe_mode", "auto"),
        agent_model=getattr(args, "agent_model", None) or defaults["agent_model"],
    )


def preview(args: argparse.Namespace) -> int:
    workspace = _load_workspace(_workspace_path(args.config))
    try:
        estimate = _estimate_from_args(args, workspace)
    except Exception as ex:
        return _print_error(ex, args.json)
    if args.json:
        _emit(estimate, True)
        return 0
    print("Voidscape preview")
    print(video._fmt_estimate(estimate))
    if estimate["requires_cloud_approval"]:
        print("Next: obtain consent, then use read with --allow-cloud.")
    elif estimate["needs_model_download"]:
        print("Next: obtain consent, then use read with --allow-model-download.")
    elif estimate["needs_install"]:
        print("Next: install the selected local backend or choose a backend already available.")
    else:
        print("Next: evidence can be prepared locally with voidscape.py read.")
    return 0


def read(args: argparse.Namespace) -> int:
    workspace = _load_workspace(_workspace_path(args.config))
    try:
        estimate = _estimate_from_args(args, workspace)
        if estimate["requires_cloud_approval"] and not args.allow_cloud:
            raise PermissionError("cloud audio processing needs explicit consent; review preview, then rerun with --allow-cloud")
        if estimate["needs_model_download"] and not args.allow_model_download:
            raise PermissionError("a local model download needs explicit consent; review preview, then rerun with --allow-model-download")
        if estimate["needs_install"]:
            raise RuntimeError("the selected local backend is not installed; choose captions or install the backend before reading")
        result = video.run(
            args.input,
            tier=estimate["tier"], frames=args.frames,
            backend=estimate["backend"], start=args.start, end=args.end,
            workdir=args.workdir, timestamps=args.timestamps, dedup=not args.no_dedup,
            transcribe_mode=args.transcribe_mode, allow_cloud=args.allow_cloud,
            allow_model_download=args.allow_model_download,
        )
    except Exception as ex:
        return _print_error(ex, args.json)
    if args.json:
        _emit(result, True)
        return 0
    print("Voidscape prepared evidence")
    print(f"  Folder: {result['workdir']}")
    print(f"  Frames: {len(result['frames'])} (deduplicated: {result['frames_deduped']})")
    print(f"  Transcript: {result['transcript'] or 'not created'}")
    print("Next: ask your agent to read manifest.json, transcript.txt, and frames/ with [MM:SS] citations.")
    return 0


def _legacy_workspace() -> Path:
    return SKILL_ROOT.parent / "read-video" / "workspace.json"


def _default_library() -> Path:
    return Path.home() / "Documents" / "Voidscape" / "Library"


def _default_inbox() -> Path:
    return Path.home() / "Documents" / "Voidscape" / "Inbox"


def _ask(prompt: str, default: str) -> str:
    answer = input(f"{prompt} [{default}]: ").strip()
    return answer or default


def customize(args: argparse.Namespace) -> int:
    path = _workspace_path(args.config)
    current = _load_workspace(path)
    legacy_path = Path(args.import_read_video).expanduser() if args.import_read_video else _legacy_workspace()
    imported: dict[str, Any] = {}
    if args.import_read_video and legacy_path.exists():
        imported = _load_workspace(legacy_path)
    base = {**current, **imported}
    interactive = not any((args.inbox, args.library, args.backend, args.whisper_model,
                           args.thorough_threshold, args.import_read_video))
    if interactive and not sys.stdin.isatty():
        print("customize needs flags in a non-interactive session; see voidscape.py customize --help", file=sys.stderr)
        return 2
    if interactive:
        print("Voidscape customize — local folders and defaults only. API keys are never stored here.")
        args.inbox = _ask("Inbox folder", str(base.get("inbox_dir", _default_inbox())))
        args.library = _ask("Library folder", str(base.get("out_dir", _default_library())))
        args.backend = _ask("Default backend", str(base.get("default_backend", "captions")))
        args.whisper_model = _ask("Local Whisper model", str(base.get("whisper_model", "small")))
        args.thorough_threshold = float(_ask("Thorough-audio threshold in seconds", str(base.get("transcription_thorough_threshold_s", 45))))
    data = {
        "_comment": "Voidscape local preferences. Keep this file private; it contains paths, never API keys.",
        "inbox_dir": args.inbox or base.get("inbox_dir") or str(_default_inbox()),
        "out_dir": args.library or base.get("out_dir") or str(_default_library()),
        "default_tier": base.get("default_tier", "both"),
        "default_backend": args.backend or base.get("default_backend", "captions"),
        "whisper_model": args.whisper_model or base.get("whisper_model", "small"),
        "transcription_thorough_threshold_s": args.thorough_threshold if args.thorough_threshold is not None else base.get("transcription_thorough_threshold_s", 45),
    }
    print("Voidscape setup preview")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    if args.import_read_video:
        print(f"Legacy config considered: {legacy_path}")
    if not args.yes:
        print("No files changed. Re-run with --yes to save these preferences.")
        return 0
    for folder in (Path(data["inbox_dir"]), Path(data["out_dir"])):
        if not folder.exists() and not args.create_dirs:
            print(f"Folder does not exist: {folder}. Re-run with --create-dirs to create it.", file=sys.stderr)
            return 3
    if args.create_dirs:
        for folder in (Path(data["inbox_dir"]), Path(data["out_dir"])):
            folder.mkdir(parents=True, exist_ok=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Saved local Voidscape preferences to {path}")
    return 0


def doctor(args: argparse.Namespace) -> int:
    workspace_path = _workspace_path(args.config)
    workspace = _load_workspace(workspace_path)
    tools = {name: shutil.which(name) is not None for name in ("python", "ffmpeg", "ffprobe", "yt-dlp")}
    report = {
        "skill_root": str(SKILL_ROOT),
        "workspace": str(workspace_path),
        "workspace_configured": bool(workspace),
        "tools": tools,
        "local_backend_available": video._have("faster_whisper"),
        "ready": tools["ffmpeg"] and tools["ffprobe"],
    }
    if args.json:
        _emit(report, True)
        return 0
    print("Voidscape doctor")
    for name, available in tools.items():
        print(f"  {'OK' if available else 'MISSING'} {name}")
    print(f"  {'OK' if workspace else 'OPTIONAL'} workspace: {workspace_path}")
    print(f"  {'OK' if report['local_backend_available'] else 'OPTIONAL'} faster-whisper")
    print("  Ready for local video analysis." if report["ready"] else "  Install ffmpeg and ffprobe before analysis.")
    return 0 if report["ready"] else 5


def _add_analysis_options(parser: argparse.ArgumentParser, include_run: bool = False) -> None:
    parser.add_argument("input")
    parser.add_argument("--tier", choices=["visual", "audio", "both"])
    parser.add_argument("--backend")
    parser.add_argument("--frames", type=int)
    parser.add_argument("--out-words", type=int, default=600)
    parser.add_argument("--transcribe-mode", choices=["auto", "fast", "thorough"], default="auto")
    parser.add_argument("--agent-model")
    parser.add_argument("--config", help="Voidscape workspace preferences file")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of guided text")
    if include_run:
        parser.add_argument("--start", type=float, default=0.0)
        parser.add_argument("--end", type=float)
        parser.add_argument("--workdir")
        parser.add_argument("--timestamps")
        parser.add_argument("--no-dedup", action="store_true")
        parser.add_argument("--allow-cloud", action="store_true")
        parser.add_argument("--allow-model-download", action="store_true")


def main(argv: list[str] | None = None) -> int:
    args_list = list(sys.argv[1:] if argv is None else argv)
    if not args_list:
        print(WELCOME)
        return 0

    parser = argparse.ArgumentParser(prog="voidscape.py", description="guided local-first media analysis")
    commands = parser.add_subparsers(dest="command", required=True)
    inspect_parser = commands.add_parser("inspect", help="inspect source facts and recommended scope")
    inspect_parser.add_argument("input")
    inspect_parser.add_argument("--json", action="store_true")
    inspect_parser.set_defaults(handler=inspect_source)
    preview_parser = commands.add_parser("preview", help="preview cost, privacy, and dependencies")
    _add_analysis_options(preview_parser)
    preview_parser.set_defaults(handler=preview)
    read_parser = commands.add_parser("read", help="prepare approved frames and transcript")
    _add_analysis_options(read_parser, include_run=True)
    read_parser.set_defaults(handler=read)
    customize_parser = commands.add_parser("customize", help="preview or save local preferences")
    customize_parser.add_argument("--inbox")
    customize_parser.add_argument("--library")
    customize_parser.add_argument("--backend")
    customize_parser.add_argument("--whisper-model")
    customize_parser.add_argument("--thorough-threshold", type=float)
    customize_parser.add_argument("--import-read-video", nargs="?", const=str(_legacy_workspace()))
    customize_parser.add_argument("--config")
    customize_parser.add_argument("--create-dirs", action="store_true")
    customize_parser.add_argument("--yes", action="store_true")
    customize_parser.set_defaults(handler=customize)
    doctor_parser = commands.add_parser("doctor", help="check local readiness without changing anything")
    doctor_parser.add_argument("--config")
    doctor_parser.add_argument("--json", action="store_true")
    doctor_parser.set_defaults(handler=doctor)
    args = parser.parse_args(args_list)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
