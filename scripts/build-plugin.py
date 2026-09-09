"""Synchronize the canonical Voidscape skill into the local Codex plugin bundle."""
from __future__ import annotations

import argparse
import os
import stat
import sys
import uuid
from contextlib import ExitStack
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "skill"
DESTINATION = REPO / "plugins" / "voidscape" / "skills" / "voidscape"
IGNORED_NAMES = {"__pycache__", "workspace.json"}
IGNORED_SOURCE_NAMES = {".env", ".credentials.json", "load-env.ps1"}


def _windows_handle(path: Path, *, directory: bool):
    """Open the object itself and deny name replacement while it is in use."""
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                  wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD,
                                  wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.GetFileInformationByHandleEx.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                                   wintypes.LPVOID, wintypes.DWORD]
    # FILE_SHARE_DELETE is deliberately absent. OPEN_REPARSE_POINT prevents following
    # a junction/symlink before the attributes of the actual opened object are checked.
    handle = kernel.CreateFileW(str(path), 0x80000000,
                                3 if directory else 1, None, 3, 0x02200000, None)
    if handle == wintypes.HANDLE(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    attributes = (wintypes.DWORD * 2)()
    try:
        if not kernel.GetFileInformationByHandleEx(handle, 9, attributes, ctypes.sizeof(attributes)):
            raise ctypes.WinError(ctypes.get_last_error())
        if attributes[0] & 0x400:
            raise RuntimeError("plugin paths cannot contain symlinks or reparse points")
        if bool(attributes[0] & 0x10) != directory:
            raise RuntimeError("plugin path changed type")
    except BaseException:
        kernel.CloseHandle(handle)
        raise
    return handle, kernel.CloseHandle


class _Directory:
    """Descriptor-relative POSIX operations; rename-locked directories on Windows."""

    def __init__(self, path: Path, stack: ExitStack, parent=None):
        self.path = path
        self.stack = stack
        if os.name == "nt":
            handle, close = _windows_handle(path, directory=True)
            stack.callback(close, handle)
            self.fd = None
        else:
            self.fd = os.open(path.name if parent else path,
                              os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                              dir_fd=parent.fd if parent else None)
            stack.callback(os.close, self.fd)

    def child(self, name: str, *, create: bool = False):
        if Path(name).name != name or name in {".", ".."}:
            raise ValueError("expected a single directory component")
        if create:
            try:
                self.mkdir(name)
            except FileExistsError:
                pass
        return _Directory(self.path / name, self.stack, self)

    def mkdir(self, name):
        if self.fd is None:
            (self.path / name).mkdir()
        else:
            os.mkdir(name, mode=0o700, dir_fd=self.fd)

    def names(self):
        return os.listdir(self.path if self.fd is None else self.fd)

    def info(self, name):
        if self.fd is None:
            return (self.path / name).lstat()
        return os.stat(name, dir_fd=self.fd, follow_symlinks=False)

    def read(self, name):
        if self.fd is None:
            import msvcrt
            handle, close = _windows_handle(self.path / name, directory=False)
            try:
                fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
            except BaseException:
                close(handle)
                raise
        else:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.fd)
        with os.fdopen(fd, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise RuntimeError("plugin source must be a regular file")
            return stream.read()

    def write(self, name, content):
        if self.fd is None:
            with (self.path / name).open("xb") as stream:
                stream.write(content)
        else:
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=self.fd)
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)

    def rename(self, name, target, target_name):
        if self.fd is None:
            (self.path / name).rename(target.path / target_name)
        else:
            os.rename(name, target_name, src_dir_fd=self.fd, dst_dir_fd=target.fd)


def _anchor(path: Path, stack: ExitStack, *, create=False):
    path = path.absolute()
    directory = _Directory(Path(path.anchor), stack)
    for part in path.parts[1:]:
        directory = directory.child(part, create=create)
    return directory


def _snapshot(directory, *, source, prefix=Path()):
    files = {}
    for name in directory.names():
        relative = prefix / name
        info = directory.info(name)
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise RuntimeError(f"plugin bundle cannot contain symlinks: {relative}")
        if stat.S_ISDIR(info.st_mode):
            files.update(_snapshot(directory.child(name), source=source, prefix=relative))
        elif not stat.S_ISREG(info.st_mode):
            raise RuntimeError(f"plugin bundle requires regular files: {relative}")
        elif not source or not (
            any(part in IGNORED_NAMES for part in relative.parts)
            or relative.suffix == ".pyc" or name in IGNORED_SOURCE_NAMES
            or name.startswith(".env.") or relative.suffix.casefold() in {".key", ".pem"}
        ):
            files[relative] = directory.read(name)
    return files


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
    with ExitStack() as stack:
        source_files = _snapshot(_anchor(SOURCE, stack), source=True)
        try:
            destination = _anchor(DESTINATION, stack)
        except FileNotFoundError:
            destination_files = {}
        else:
            destination_files = _snapshot(destination, source=False)
    errors: list[str] = []
    for relative in sorted(source_files):
        target = destination_files.get(relative)
        if target is None:
            errors.append(f"missing: {relative}")
        elif source_files[relative] != target:
            errors.append(f"out of date: {relative}")
    for relative in sorted(destination_files.keys() - source_files.keys()):
        errors.append(f"unexpected: {relative}")
    return errors


def sync() -> None:
    with ExitStack() as stack:
        source_files = _snapshot(_anchor(SOURCE, stack), source=True)
    with ExitStack() as stack:
        parent = _anchor(DESTINATION.parent, stack, create=True)
        had_destination = DESTINATION.name in parent.names()
        if had_destination:
            with ExitStack() as inspection:
                root = _Directory(DESTINATION, inspection, parent)
                _snapshot(root, source=False)
        stage_name = ".plugin-stage-" + uuid.uuid4().hex
        parent.mkdir(stage_name)
        staging = parent.child(stage_name)
        staging.mkdir("replacement")
        with ExitStack() as writing:
            replacement = _Directory(staging.path / "replacement", writing, staging)
            for relative, content in source_files.items():
                target = replacement
                for part in relative.parts[:-1]:
                    target = target.child(part, create=True)
                target.write(relative.name, content)
        if had_destination:
            parent.rename(DESTINATION.name, staging, "previous")
        try:
            staging.rename("replacement", parent, DESTINATION.name)
        except OSError:
            if had_destination and DESTINATION.name not in parent.names():
                staging.rename("previous", parent, DESTINATION.name)
            raise
        if had_destination:
            print(f"Previous plugin tree preserved at: {staging.path / 'previous'}")


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
