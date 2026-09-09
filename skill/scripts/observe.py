#!/usr/bin/env python3
"""On-demand local screenshots, short silent clips, and optional companion health."""
from __future__ import annotations

import argparse
import http.client
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse


PROTOCOL_VERSION = "1.0"
DEFAULT_SCREENPIPE_URL = "http://127.0.0.1:3030"
MAX_CLIP_SECONDS = 300
_EXIT_UNEXPECTED = 1
_EXIT_USAGE = 2
_EXIT_INPUT = 3
_EXIT_APPROVAL = 4
_EXIT_DEPENDENCY = 5
_EXIT_OPERATION = 6


class ObserveError(RuntimeError):
    def __init__(self, message: str, *, code: str, exit_code: int,
                 retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.exit_code = exit_code
        self.retryable = retryable


def _input_error(message: str) -> ObserveError:
    return ObserveError(message, code="input_error", exit_code=_EXIT_INPUT)


def _dependency_error(message: str) -> ObserveError:
    return ObserveError(message, code="dependency_error", exit_code=_EXIT_DEPENDENCY)


def _operation_error(message: str, *, retryable: bool = False) -> ObserveError:
    return ObserveError(
        message, code="operation_failed", exit_code=_EXIT_OPERATION, retryable=retryable,
    )


def _json_text(value: dict[str, Any], compact: bool = False) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":") if compact else None,
        indent=None if compact else 2,
    )


def _envelope(data: dict[str, Any] | None, error: dict[str, Any] | None,
              command: str | None) -> dict[str, Any]:
    return {
        "ok": error is None,
        "data": data,
        "error": error,
        "meta": {"command": command, "protocol_version": PROTOCOL_VERSION},
    }


def _machine_output(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "json", False) or getattr(args, "envelope", False))


def _emit_success(data: dict[str, Any], args: argparse.Namespace) -> None:
    if _machine_output(args):
        print(_json_text(_envelope(data, None, args.command), args.compact))


def _emit_error(error: ObserveError, command: str | None,
                machine: bool, compact: bool) -> int:
    if machine:
        payload = {
            "code": error.code,
            "message": str(error),
            "retryable": error.retryable,
            "exit_code": error.exit_code,
        }
        print(_json_text(_envelope(None, payload, command), compact))
    else:
        print(f"Observe could not continue: {error}", file=sys.stderr)
    return error.exit_code


class _ObserveArgumentParser(argparse.ArgumentParser):
    machine_errors = False
    compact_errors = False
    error_command: str | None = None

    def error(self, message: str) -> None:
        if type(self).machine_errors:
            error = {
                "code": "usage_error",
                "message": message,
                "retryable": False,
                "exit_code": _EXIT_USAGE,
            }
            print(_json_text(
                _envelope(None, error, type(self).error_command),
                type(self).compact_errors,
            ))
            raise SystemExit(_EXIT_USAGE)
        super().error(message)


def _system_name() -> str:
    current = platform.system().casefold()
    if current == "windows":
        return "windows"
    if current == "linux":
        return "linux"
    if current == "darwin":
        return "macos"
    return current or "unknown"


def _capture_profile(display: str | None = None) -> dict[str, Any]:
    system = _system_name()
    if system == "windows":
        if display:
            raise _input_error("--display is supported only for Linux X11 capture")
        return {
            "platform": system,
            "capture_supported": True,
            "capture_backend": "gdigrab",
            "display": "desktop",
        }
    if system == "linux":
        session_type = os.environ.get("XDG_SESSION_TYPE", "").casefold()
        selected_display = display or os.environ.get("DISPLAY")
        if session_type == "wayland":
            return {
                "platform": system,
                "capture_supported": False,
                "capture_backend": None,
                "display": selected_display,
                "reason": "Wayland capture is unsupported in observe v1",
            }
        if not selected_display:
            return {
                "platform": system,
                "capture_supported": False,
                "capture_backend": "x11grab",
                "display": None,
                "reason": "Linux X11 capture needs DISPLAY or --display",
            }
        return {
            "platform": system,
            "capture_supported": True,
            "capture_backend": "x11grab",
            "display": selected_display,
        }
    return {
        "platform": system,
        "capture_supported": False,
        "capture_backend": None,
        "display": None,
        "reason": f"{system} capture is unsupported in observe v1",
    }


def _validate_screenpipe_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "http":
        raise _input_error("screenpipe URL must use loopback HTTP")
    if parsed.username or parsed.password:
        raise _input_error("screenpipe URL must not contain credentials")
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise _input_error("screenpipe URL must use a loopback host")
    try:
        parsed.port
    except ValueError as ex:
        raise _input_error("screenpipe URL has an invalid port") from ex
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise _input_error("screenpipe URL must be a loopback origin without a path or query")
    return value.rstrip("/")


def _fetch_health(url: str) -> dict[str, Any] | None:
    parsed = urlparse(_validate_screenpipe_url(url))
    host = "::1" if parsed.hostname == "::1" else "127.0.0.1"
    connection = http.client.HTTPConnection(host, parsed.port or 80, timeout=2)
    try:
        # Direct loopback transport never consults proxies or follows redirects.
        connection.request("GET", "/health", headers={"Accept": "application/json"})
        response = connection.getresponse()
        if response.status != 200:
            return None
        raw = response.read(1_048_577)
    except (http.client.HTTPException, HTTPError, URLError, TimeoutError, OSError):
        return None
    finally:
        connection.close()
    if len(raw) > 1_048_576:
        raise _operation_error("screenpipe health response exceeded the safe size limit")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as ex:
        raise _operation_error("screenpipe health response was not valid JSON") from ex
    if not isinstance(payload, dict):
        raise _operation_error("screenpipe health response was not a JSON object")
    return payload


def _normalize_screenpipe(payload: dict[str, Any], *, installed: bool,
                          source: str) -> dict[str, Any]:
    health = payload.get("health")
    health = health if isinstance(health, dict) else payload
    return {
        "installed": installed,
        "reachable": True,
        "source": source,
        "running": payload.get("running", True),
        "health_status": health.get("status"),
        "frame_status": health.get("frame_status"),
        "audio_status": health.get("audio_status"),
        "last_capture": payload.get("last_capture", health.get("last_capture")),
        "last_audio_capture": payload.get(
            "last_audio_capture", health.get("last_audio_capture"),
        ),
    }


def screenpipe_status(screenpipe_url: str = DEFAULT_SCREENPIPE_URL) -> dict[str, Any]:
    url = _validate_screenpipe_url(screenpipe_url)
    executable = shutil.which("screenpipe")
    if executable:
        try:
            result = subprocess.run(
                [executable, "status", "--json"],
                capture_output=True,
                text=True,
                timeout=3,
                shell=False,
            )
        except (subprocess.TimeoutExpired, OSError):
            return {"installed": True, "reachable": False, "source": "cli"}
        if result.returncode != 0:
            return {"installed": True, "reachable": False, "source": "cli"}
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as ex:
            raise _operation_error("screenpipe status response was not valid JSON") from ex
        if not isinstance(payload, dict):
            raise _operation_error("screenpipe status response was not a JSON object")
        return _normalize_screenpipe(payload, installed=True, source="cli")

    payload = _fetch_health(url)
    if payload is None:
        return {"installed": False, "reachable": False, "source": None}
    return _normalize_screenpipe(payload, installed=False, source="health_endpoint")


def doctor_report(screenpipe_url: str = DEFAULT_SCREENPIPE_URL,
                  *, check_screenpipe: bool = True) -> dict[str, Any]:
    profile = _capture_profile()
    report = {
        **profile,
        "tools": {
            "ffmpeg": shutil.which("ffmpeg") is not None,
            "ffprobe": shutil.which("ffprobe") is not None,
            "screenpipe": shutil.which("screenpipe") is not None,
        },
        "screenpipe": {"reachable": False, "source": None},
    }
    if check_screenpipe:
        status = screenpipe_status(screenpipe_url)
        report["screenpipe"] = {
            "reachable": status["reachable"],
            "source": status["source"],
        }
    return report


def _validate_output(value: str, suffix: str) -> Path:
    output = Path(value).expanduser().absolute()
    if output.suffix.casefold() != suffix:
        raise _input_error(f"output must use the {suffix} extension")
    if output.exists() or output.is_symlink():
        raise _input_error(f"output already exists: {output}")
    if not output.parent.is_dir():
        raise _input_error(f"output parent directory does not exist: {output.parent}")
    return output


def _capture_input(display: str | None) -> tuple[str, dict[str, Any]]:
    profile = _capture_profile(display)
    if not profile["capture_supported"]:
        raise _dependency_error(profile.get("reason") or "capture is unsupported")
    executable = shutil.which("ffmpeg")
    if not executable:
        raise _dependency_error("ffmpeg is not installed or not on PATH")
    return executable, profile


def _remove_partial(output: Path) -> None:
    try:
        output.unlink(missing_ok=True)
    except OSError:
        pass


def _run_capture(argv: list[str], output: Path, timeout: int) -> None:
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
    except subprocess.TimeoutExpired as ex:
        _remove_partial(output)
        raise _operation_error("screen capture timed out", retryable=True) from ex
    except (PermissionError, OSError) as ex:
        _remove_partial(output)
        raise _operation_error(
            "screen capture could not start; check OS screen-recording permission",
        ) from ex
    if result.returncode != 0:
        _remove_partial(output)
        raise _operation_error(
            "screen capture failed; check OS screen-recording permission and display availability",
        )
    if not output.is_file() or output.stat().st_size <= 0:
        _remove_partial(output)
        raise _operation_error("screen capture completed without a non-empty output file")


def screenshot(out: str, display: str | None = None) -> dict[str, Any]:
    output = _validate_output(out, ".png")
    executable, profile = _capture_input(display)
    argv = [
        executable, "-hide_banner", "-loglevel", "error", "-n",
        "-f", profile["capture_backend"], "-framerate", "1",
        "-i", profile["display"], "-frames:v", "1", str(output),
    ]
    _run_capture(argv, output, timeout=30)
    return {
        "path": str(output),
        "media_type": "image",
        "bytes": output.stat().st_size,
        "backend": profile["capture_backend"],
        "platform": profile["platform"],
    }


def clip(out: str, seconds: int, display: str | None = None) -> dict[str, Any]:
    if not 1 <= seconds <= MAX_CLIP_SECONDS:
        raise _input_error(f"--seconds must be between 1 and {MAX_CLIP_SECONDS}")
    output = _validate_output(out, ".mp4")
    executable, profile = _capture_input(display)
    argv = [
        executable, "-hide_banner", "-loglevel", "error", "-n",
        "-f", profile["capture_backend"], "-framerate", "15",
        "-i", profile["display"], "-t", str(seconds),
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        str(output),
    ]
    _run_capture(argv, output, timeout=seconds + 30)
    return {
        "path": str(output),
        "media_type": "video",
        "seconds": seconds,
        "bytes": output.stat().st_size,
        "backend": profile["capture_backend"],
        "platform": profile["platform"],
    }


def _print_doctor(report: dict[str, Any]) -> None:
    print("Voidscape observe doctor")
    for tool, available in report["tools"].items():
        label = "OK" if available else ("OPTIONAL" if tool == "screenpipe" else "MISSING")
        print(f"  {label} {tool}")
    if report["capture_supported"]:
        print(f"  OK capture: {report['capture_backend']} ({report['display']})")
    else:
        print(f"  UNSUPPORTED capture: {report.get('reason', report['platform'])}")
    state = "reachable" if report["screenpipe"]["reachable"] else "not reachable (optional)"
    print(f"  screenpipe: {state}")


def _print_status(report: dict[str, Any]) -> None:
    state = "reachable" if report["screenpipe"]["reachable"] else "not reachable"
    print(f"screenpipe: {state} (optional)")
    if report["screenpipe"].get("health_status"):
        print(f"  health: {report['screenpipe']['health_status']}")
    if report["screenpipe"].get("last_capture"):
        print(f"  last capture: {report['screenpipe']['last_capture']}")


def _add_output_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="emit standard JSON envelope")
    parser.add_argument("--envelope", action="store_true", help="alias for --json")
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")


def _parser() -> argparse.ArgumentParser:
    parser = _ObserveArgumentParser(
        prog="observe.py", description="on-demand local screenshot and short-clip capture",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    doctor_parser = commands.add_parser("doctor", help="check capture and companion readiness")
    doctor_parser.add_argument("--screenpipe-url", default=DEFAULT_SCREENPIPE_URL)
    _add_output_flags(doctor_parser)

    screenshot_parser = commands.add_parser("screenshot", help="capture one local PNG")
    screenshot_parser.add_argument("--out", required=True)
    screenshot_parser.add_argument("--display")
    _add_output_flags(screenshot_parser)

    clip_parser = commands.add_parser("clip", help="capture a short silent MP4")
    clip_parser.add_argument("--seconds", required=True, type=int)
    clip_parser.add_argument("--out", required=True)
    clip_parser.add_argument("--display")
    _add_output_flags(clip_parser)

    status_parser = commands.add_parser("status", help="report optional screenpipe health")
    status_parser.add_argument("--screenpipe-url", default=DEFAULT_SCREENPIPE_URL)
    _add_output_flags(status_parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    args_list = list(sys.argv[1:] if argv is None else argv)
    command = next((arg for arg in args_list if arg in {
        "doctor", "screenshot", "clip", "status",
    }), None)
    machine = "--json" in args_list or "--envelope" in args_list
    compact = "--compact" in args_list
    _ObserveArgumentParser.machine_errors = machine
    _ObserveArgumentParser.compact_errors = compact
    _ObserveArgumentParser.error_command = command
    args = _parser().parse_args(args_list)
    try:
        if args.command == "doctor":
            data = doctor_report(args.screenpipe_url)
            _emit_success(data, args)
            if not _machine_output(args):
                _print_doctor(data)
            return 0
        if args.command == "status":
            data = {
                "platform": _system_name(),
                "capture_supported": _capture_profile()["capture_supported"],
                "screenpipe": screenpipe_status(args.screenpipe_url),
            }
            _emit_success(data, args)
            if not _machine_output(args):
                _print_status(data)
            return 0
        if args.command == "screenshot":
            data = screenshot(args.out, args.display)
        else:
            data = clip(args.out, args.seconds, args.display)
        _emit_success(data, args)
        if not _machine_output(args):
            print(f"Captured {data['media_type']}: {data['path']}")
            print(f"Next: voidscape.py inspect {data['path']!r}")
        return 0
    except ObserveError as ex:
        return _emit_error(ex, args.command, _machine_output(args), args.compact)
    except Exception:
        unexpected = ObserveError(
            "unexpected observe error",
            code="unexpected_error",
            exit_code=_EXIT_UNEXPECTED,
        )
        return _emit_error(unexpected, args.command, _machine_output(args), args.compact)


if __name__ == "__main__":
    sys.exit(main())
