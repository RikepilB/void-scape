"""Voidscape's guided, human-friendly front door for the stable read-video engine."""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Any

if __package__:
    from . import article as article_engine
    from . import image as image_engine
    from . import observe as observe_engine
    from . import video
else:
    import article as article_engine
    import image as image_engine
    import observe as observe_engine
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

  init                    Install the agent skill and check readiness.
  customize               Choose local folders and defaults (optional).
  doctor                  Check local readiness without changing anything.

Start here:
  voidscape init
  voidscape inspect "meeting.mp4"

Agent workflow:
  /voidscape <file-or-url>
""".strip()


SKILL_ROOT = Path(__file__).resolve().parent.parent
LOCAL_WORKSPACE_PATH = SKILL_ROOT / "workspace.json"
USER_WORKSPACE_PATH = Path.home() / ".voidscape" / "workspace.json"
WORKSPACE_PATH = LOCAL_WORKSPACE_PATH if LOCAL_WORKSPACE_PATH.exists() else USER_WORKSPACE_PATH


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
        "backend": workspace.get("default_backend"),
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


def _is_image_source(value: str) -> bool:
    if video.is_url(value):
        return False
    return image_engine.is_image_input(video.resolve_input(value))


def _is_article_source(value: str) -> bool:
    return article_engine.is_article_input(video.resolve_input(value))


def _print_image_skipped(result: dict[str, Any]) -> None:
    skipped = result.get("skipped") or []
    if skipped:
        details = ", ".join(
            f"{entry['name']} ({entry['reason']})" for entry in skipped
        )
        print(f"  Skipped: {details}")


def _print_article_skipped(result: dict[str, Any]) -> None:
    skipped = result.get("skipped") or []
    if skipped:
        details = ", ".join(
            f"{entry.get('title') or entry.get('name', '?')} ({entry['reason']})"
            for entry in skipped
        )
        print(f"  Skipped: {details}")


def inspect_source(args: argparse.Namespace) -> int:
    try:
        image_source = _is_image_source(args.input)
        article_source = False if image_source else _is_article_source(args.input)
        if image_source:
            info = image_engine.probe(args.input)
        elif article_source:
            info = article_engine.probe(args.input)
        else:
            info = video.probe(args.input)
    except Exception as ex:
        return _print_error(ex, args.json)
    if args.json:
        _emit(info, True)
        return 0
    if image_source:
        label = "Carousel" if info["kind"] == "carousel" else "Image"
        count_label = "image" if info["item_count"] == 1 else "images"
        print("Voidscape inspection")
        print(f"  {label}: {info['item_count']} {count_label}")
        print("  Order: " + ", ".join(item["source_name"] for item in info["images"]))
        _print_image_skipped(info)
        print("  Processing: local only · originals preserved")
        print(f"Next: voidscape preview {args.input!r}")
        return 0
    if article_source:
        label = "Feed" if info["kind"] == "feed" else "Article"
        count_label = "entry" if info["item_count"] == 1 else "entries"
        print("Voidscape inspection")
        print(f"  {label}: {info['item_count']} {count_label}")
        if info.get("feed_title"):
            print(f"  Feed title: {info['feed_title']}")
        print("  Order: " + ", ".join(item["title"] for item in info["entries"]))
        _print_article_skipped(info)
        if info.get("requires_fetch_approval"):
            print("  Availability: remote URL · fetch requires explicit approval")
        else:
            print("  Processing: local only · originals preserved")
        print(f"Next: voidscape preview {args.input!r}")
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
    print(f"Next: voidscape preview {args.input!r}")
    return 0


def _estimate_from_args(args: argparse.Namespace, workspace: dict[str, Any]) -> dict[str, Any]:
    defaults = _defaults(workspace)
    backend = (getattr(args, "backend", None) or defaults["backend"]
               or ("captions" if video.is_url(args.input) else "faster-whisper"))
    return video.estimate(
        args.input,
        getattr(args, "frames", None),
        backend,
        getattr(args, "out_words", 600),
        getattr(args, "tier", None) or defaults["tier"],
        transcribe_mode=getattr(args, "transcribe_mode", "auto"),
        agent_model=getattr(args, "agent_model", None) or defaults["agent_model"],
    )


def preview(args: argparse.Namespace) -> int:
    workspace = _load_workspace(_workspace_path(args.config))
    try:
        image_source = _is_image_source(args.input)
        article_source = False if image_source else _is_article_source(args.input)
        agent_model = args.agent_model or _defaults(workspace)["agent_model"]
        if image_source:
            estimate = image_engine.estimate(args.input, args.out_words, agent_model)
        elif article_source:
            estimate = article_engine.estimate(args.input, args.out_words, agent_model)
        else:
            estimate = _estimate_from_args(args, workspace)
    except Exception as ex:
        return _print_error(ex, args.json)
    if args.json:
        _emit(estimate, True)
        return 0
    print("Voidscape preview")
    if image_source:
        print(image_engine._fmt_estimate(estimate))
    elif article_source:
        print(article_engine._fmt_estimate(estimate))
    else:
        print(video._fmt_estimate(estimate))
    if image_source:
        _print_image_skipped(estimate)
        print("Next: evidence can be prepared locally with voidscape read.")
        return 0
    if article_source:
        _print_article_skipped(estimate)
        if estimate.get("requires_fetch_approval"):
            print("Next: obtain consent, then use read with --allow-cloud.")
        else:
            print("Next: evidence can be prepared locally with voidscape read.")
        return 0
    if estimate["requires_cloud_approval"]:
        print("Next: obtain consent, then use read with --allow-cloud.")
    elif estimate["needs_model_download"]:
        print("Next: obtain consent, then use read with --allow-model-download.")
    elif estimate["needs_install"]:
        print("Next: install the selected local backend or choose a backend already available.")
    else:
        print("Next: evidence can be prepared locally with voidscape read.")
    return 0


def read(args: argparse.Namespace) -> int:
    workspace = _load_workspace(_workspace_path(args.config))
    try:
        image_source = _is_image_source(args.input)
        article_source = False if image_source else _is_article_source(args.input)
        if image_source:
            result = image_engine.run(args.input, args.workdir)
        elif article_source:
            estimate = article_engine.estimate(
                args.input, args.out_words,
                args.agent_model or _defaults(workspace)["agent_model"],
            )
            if estimate["requires_cloud_approval"] and not args.allow_cloud:
                raise PermissionError(
                    "remote article fetch needs explicit consent; review preview, "
                    "then rerun with --allow-cloud"
                )
            result = article_engine.run(
                args.input, args.workdir, allow_fetch=args.allow_cloud,
            )
        else:
            image_source = False
            article_source = False
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
    if image_source:
        print(f"  Images: {result['item_count']}")
        print("Next: ask your agent to read manifest.json and images/ with [image 1] citations.")
        return 0
    if article_source:
        print(f"  Entries: {result['item_count']}")
        print(f"Next: ask your agent to read manifest.json and entries/ with {result['citation_guide']}.")
        return 0
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


def _copy_skill_tree(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        if item.name in {"workspace.json", ".env", "load-env.ps1", "__pycache__"}:
            continue
        target = destination / item.name
        if item.is_dir():
            shutil.copytree(
                item, target, dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
        else:
            shutil.copy2(item, target)


def _verify_skill(destination: Path) -> None:
    skill_md = destination / "SKILL.md"
    cli = destination / "scripts" / "voidscape.py"
    if not skill_md.is_file() or not cli.is_file():
        raise RuntimeError(f"agent skill verification failed at {destination}")
    frontmatter = skill_md.read_text(encoding="utf-8")
    if not frontmatter.startswith("---\n") or "name:" not in frontmatter:
        raise RuntimeError(f"agent skill frontmatter is invalid at {destination}")


def _ffmpeg_install_hint() -> str:
    system = platform.system()
    if system == "Windows":
        return "winget install --id=Gyan.FFmpeg -e"
    if system == "Darwin":
        return "brew install ffmpeg"
    return "sudo apt update && sudo apt install ffmpeg"


def init(args: argparse.Namespace) -> int:
    roots = [] if args.no_skill else [
        ("Codex", Path(args.codex_skills_root).expanduser()),
        ("shared agents", Path(args.agents_skills_root).expanduser()),
    ]
    installed: list[dict[str, str]] = []
    try:
        for harness, root in roots:
            destination = root / "voidscape"
            _copy_skill_tree(SKILL_ROOT, destination)
            _verify_skill(destination)
            installed.append({"harness": harness, "path": str(destination)})
    except Exception as ex:
        return _print_error(ex, args.json)

    tools = {
        name: shutil.which(name) is not None
        for name in ("ffmpeg", "ffprobe", "yt-dlp")
    }
    result = {
        "cli": "voidscape",
        "agent_skills": installed,
        "workspace": str(_workspace_path()),
        "tools": tools,
        "ready_for_video": tools["ffmpeg"] and tools["ffprobe"],
        "ffmpeg_install": None,
        "cloud_approved": False,
        "model_download_approved": False,
    }
    if not result["ready_for_video"]:
        result["ffmpeg_install"] = _ffmpeg_install_hint()
    if args.json:
        _emit(result, True)
        return 0

    print("Voidscape init")
    print("  OK CLI command: voidscape")
    if installed:
        for item in installed:
            print(f"  OK {item['harness']} skill: {item['path']}")
    else:
        print("  SKIPPED agent skill (--no-skill)")
    for name, available in tools.items():
        print(f"  {'OK' if available else 'MISSING'} {name}")
    print("  No cloud job or model download was approved.")
    print("Next:")
    print("  voidscape customize   # optional Inbox, Library, and local defaults")
    print("  voidscape doctor      # detailed readiness check")
    print('  voidscape inspect "meeting.mp4"')
    if not result["ready_for_video"]:
        print("Install FFmpeg and FFprobe before reading video or audio.")
        print(f"  {_ffmpeg_install_hint()}")
    return 0


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
        print("customize needs flags in a non-interactive session; see voidscape customize --help", file=sys.stderr)
        return 2
    if interactive:
        print("Voidscape customize — local folders and defaults only. API keys are never stored here.")
        args.inbox = _ask("Inbox folder", str(base.get("inbox_dir", _default_inbox())))
        args.library = _ask("Library folder", str(base.get("out_dir", _default_library())))
        args.backend = _ask("Default backend", str(base.get("default_backend", "faster-whisper")))
        args.whisper_model = _ask("Local Whisper model", str(base.get("whisper_model", "small")))
        args.thorough_threshold = float(_ask("Thorough-audio threshold in seconds", str(base.get("transcription_thorough_threshold_s", 45))))
    data = {
        "_comment": "Voidscape local preferences. Keep this file private; it contains paths, never API keys.",
        "inbox_dir": args.inbox or base.get("inbox_dir") or str(_default_inbox()),
        "out_dir": args.library or base.get("out_dir") or str(_default_library()),
        "default_tier": base.get("default_tier", "both"),
        "default_backend": args.backend or base.get("default_backend", "faster-whisper"),
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
    observe_report = observe_engine.doctor_report(check_screenpipe=False)
    report = {
        "skill_root": str(SKILL_ROOT),
        "workspace": str(workspace_path),
        "workspace_configured": bool(workspace),
        "tools": tools,
        "local_backend_available": video._have("faster_whisper"),
        "observe": {
            "capture_supported": observe_report["capture_supported"],
            "backend": observe_report["capture_backend"],
            "screenpipe_optional": True,
        },
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
    if not observe_report["capture_supported"]:
        print(f"  UNSUPPORTED observe capture: {observe_report.get('reason', observe_report['platform'])}")
    elif tools["ffmpeg"]:
        print(f"  OK observe capture: {observe_report['capture_backend']}")
    else:
        print(f"  MISSING observe capture: ffmpeg ({observe_report['capture_backend']})")
    if report["ready"]:
        print("  Ready for local video analysis.")
    else:
        print("  Install ffmpeg and ffprobe before analysis:")
        print(f"  {_ffmpeg_install_hint()}")
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

    parser = argparse.ArgumentParser(prog="voidscape", description="guided local-first media analysis")
    commands = parser.add_subparsers(dest="command", required=True)
    init_parser = commands.add_parser("init", help="install the agent skill and check readiness")
    init_parser.add_argument(
        "--codex-skills-root", default=str(Path.home() / ".codex" / "skills"),
    )
    init_parser.add_argument(
        "--agents-skills-root", default=str(Path.home() / ".agents" / "skills"),
    )
    init_parser.add_argument("--no-skill", action="store_true")
    init_parser.add_argument("--json", action="store_true")
    init_parser.set_defaults(handler=init)
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
