"""Synchronize the canonical Voidscape skill into the local Codex plugin bundle."""
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "skill"
DESTINATION = REPO / "plugins" / "voidscape" / "skills" / "voidscape"
IGNORED_NAMES = {"__pycache__", "workspace.json"}
IGNORED_SOURCE_NAMES = {".env", ".credentials.json", "load-env.ps1"}


def _files(root: Path, *, source: bool) -> dict[Path, Path]:
    files: dict[Path, Path] = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if path.is_symlink():
            raise RuntimeError(f"plugin bundle cannot contain symlinks: {relative}")
        if not path.is_file():
            continue
        if source and (
            any(part in IGNORED_NAMES for part in relative.parts)
            or path.suffix == ".pyc"
            or path.name in IGNORED_SOURCE_NAMES
            or path.name.startswith(".env.")
            or path.suffix.casefold() in {".key", ".pem"}
        ):
            continue
        files[relative] = path
    return files


def check() -> list[str]:
    source_files = _files(SOURCE, source=True)
    destination_files = _files(DESTINATION, source=False) if DESTINATION.exists() else {}
    errors: list[str] = []
    for relative in sorted(source_files):
        target = destination_files.get(relative)
        if target is None:
            errors.append(f"missing: {relative}")
        elif source_files[relative].read_bytes() != target.read_bytes():
            errors.append(f"out of date: {relative}")
    for relative in sorted(destination_files.keys() - source_files.keys()):
        errors.append(f"unexpected: {relative}")
    return errors


def sync() -> None:
    for root in (SOURCE, DESTINATION):
        if any(path.is_symlink() for path in (root, *root.parents)):
            raise RuntimeError("plugin roots cannot traverse symlinks")
    source_files = _files(SOURCE, source=True)
    if DESTINATION.exists():
        _files(DESTINATION, source=False)
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    # Stage complete content without opening any existing destination file.
    # Keep the previous tree for reversible recovery instead of deleting it.
    staging = Path(tempfile.mkdtemp(prefix=".plugin-stage-", dir=DESTINATION.parent))
    replacement = staging / "replacement"
    replacement.mkdir()
    for relative, source in source_files.items():
        target = replacement / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    backup = staging / "previous"
    had_destination = DESTINATION.exists()
    if had_destination:
        _files(DESTINATION, source=False)
        if DESTINATION.is_symlink():
            raise RuntimeError("plugin destination cannot be a symlink")
        DESTINATION.rename(backup)
    try:
        replacement.rename(DESTINATION)
    except OSError:
        if had_destination and not DESTINATION.exists():
            backup.rename(DESTINATION)
        raise
    if had_destination:
        print(f"Previous plugin tree preserved at: {backup}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="build-plugin")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    if not args.check:
        sync()
    errors = check()
    if errors:
        for error in errors:
            print(error)
        if args.check:
            print("run: python scripts/build-plugin.py")
        return 1
    print(f"plugin skill synchronized: {len(_files(SOURCE, source=True))} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
