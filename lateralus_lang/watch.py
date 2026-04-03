"""
lateralus_lang/watch.py
LATERALUS File Watcher — Hot-Reload Development Server

Watches .ltl source files and automatically recompiles/reruns on changes.
Provides both a polling-based fallback (always available) and inotify/kqueue
via the `watchdog` library (optional, much more efficient).

Usage:
    python -m lateralus_lang watch src/          # watch directory
    python -m lateralus_lang watch main.ltl      # watch single file
    python -m lateralus_lang watch src/ --run    # watch and run on change
    python -m lateralus_lang watch src/ --check  # watch and type-check only

Programmatic usage:
    watcher = FileWatcher("src/")
    watcher.on_change(lambda path: print(f"Changed: {path}"))
    watcher.start()
"""

from __future__ import annotations

import os
import sys
import time
import hashlib
import threading
import subprocess
from pathlib import Path
from typing import Callable, Optional, Union
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Change event
# ---------------------------------------------------------------------------

class ChangeKind:
    CREATED  = "created"
    MODIFIED = "modified"
    DELETED  = "deleted"
    MOVED    = "moved"


@dataclass
class FileChangeEvent:
    kind: str          # ChangeKind value
    path: Path
    old_path: Optional[Path] = None   # for MOVED events


# ---------------------------------------------------------------------------
# File hash snapshot (polling watcher core)
# ---------------------------------------------------------------------------

class _FileSnapshot:
    """Tracks a directory's file modification state via content hashing."""

    def __init__(self, root: Path, extensions: tuple[str, ...]) -> None:
        self._root = root
        self._extensions = extensions
        self._hashes: dict[str, str] = {}

    def _hash_file(self, path: Path) -> str:
        try:
            data = path.read_bytes()
            return hashlib.blake2b(data, digest_size=8).hexdigest()
        except (PermissionError, OSError):
            return ""

    def _scan(self) -> dict[str, str]:
        result: dict[str, str] = {}
        paths = [self._root] if self._root.is_file() else []
        if self._root.is_dir():
            for ext in self._extensions:
                paths.extend(self._root.rglob(f"*{ext}"))
        for p in paths:
            if p.is_file():
                result[str(p)] = self._hash_file(p)
        return result

    def diff(self) -> list[FileChangeEvent]:
        """Compare current state to snapshot, return change events."""
        current = self._scan()
        events: list[FileChangeEvent] = []

        for path_str, h in current.items():
            if path_str not in self._hashes:
                events.append(FileChangeEvent(ChangeKind.CREATED, Path(path_str)))
            elif self._hashes[path_str] != h:
                events.append(FileChangeEvent(ChangeKind.MODIFIED, Path(path_str)))

        for path_str in self._hashes:
            if path_str not in current:
                events.append(FileChangeEvent(ChangeKind.DELETED, Path(path_str)))

        self._hashes = current
        return events

    def initialize(self) -> None:
        """Take initial snapshot (no events emitted)."""
        self._hashes = self._scan()


# ---------------------------------------------------------------------------
# File watcher
# ---------------------------------------------------------------------------

class FileWatcher:
    """
    Watches .ltl files for changes and invokes registered callbacks.

    Polling-based by default. If `watchdog` is installed, uses OS-native events.
    """

    DEFAULT_EXTENSIONS = (".ltl", ".ltlml", ".ltlcfg", ".ltlnb")

    def __init__(self,
                 path: Union[str, Path],
                 extensions: Optional[tuple[str, ...]] = None,
                 interval: float = 0.5) -> None:
        self._root = Path(path).resolve()
        self._extensions = extensions or self.DEFAULT_EXTENSIONS
        self._interval = interval
        self._callbacks: list[Callable[[FileChangeEvent], None]] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._snapshot = _FileSnapshot(self._root, self._extensions)
        self._use_watchdog = self._try_watchdog()

    def _try_watchdog(self) -> bool:
        try:
            import watchdog  # type: ignore
            return True
        except ImportError:
            return False

    def on_change(self, callback: Callable[[FileChangeEvent], None]) -> "FileWatcher":
        """Register a callback for file change events."""
        self._callbacks.append(callback)
        return self

    def _emit(self, event: FileChangeEvent) -> None:
        for cb in self._callbacks:
            try:
                cb(event)
            except Exception as e:
                print(f"[watch] Callback error: {e}", file=sys.stderr)

    def start(self, block: bool = True) -> None:
        """Start watching. If block=True, runs in current thread."""
        self._snapshot.initialize()
        self._running = True
        print(f"[watch] Watching {self._root} (interval={self._interval}s)")
        print(f"[watch] Extensions: {', '.join(self._extensions)}")

        if self._use_watchdog:
            self._start_watchdog(block)
        else:
            self._start_polling(block)

    def stop(self) -> None:
        """Stop watching."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def _start_polling(self, block: bool) -> None:
        def _loop() -> None:
            while self._running:
                events = self._snapshot.diff()
                for event in events:
                    self._emit(event)
                time.sleep(self._interval)

        if block:
            try:
                _loop()
            except KeyboardInterrupt:
                print("\n[watch] Stopped.")
        else:
            self._thread = threading.Thread(target=_loop, daemon=True)
            self._thread.start()

    def _start_watchdog(self, block: bool) -> None:
        try:
            from watchdog.observers import Observer  # type: ignore
            from watchdog.events import FileSystemEventHandler, FileModifiedEvent  # type: ignore

            watcher = self

            class _Handler(FileSystemEventHandler):
                def on_modified(self, event):
                    if not event.is_directory:
                        p = Path(event.src_path)
                        if p.suffix in watcher._extensions:
                            watcher._emit(FileChangeEvent(ChangeKind.MODIFIED, p))

                def on_created(self, event):
                    if not event.is_directory:
                        p = Path(event.src_path)
                        if p.suffix in watcher._extensions:
                            watcher._emit(FileChangeEvent(ChangeKind.CREATED, p))

                def on_deleted(self, event):
                    if not event.is_directory:
                        p = Path(event.src_path)
                        if p.suffix in watcher._extensions:
                            watcher._emit(FileChangeEvent(ChangeKind.DELETED, p))

            observer = Observer()
            path = str(self._root) if self._root.is_dir() else str(self._root.parent)
            observer.schedule(_Handler(), path, recursive=True)
            observer.start()

            if block:
                try:
                    while self._running:
                        time.sleep(self._interval)
                except KeyboardInterrupt:
                    print("\n[watch] Stopped.")
                finally:
                    observer.stop()
                    observer.join()
            else:
                def _cleanup():
                    while self._running:
                        time.sleep(self._interval)
                    observer.stop()
                    observer.join()
                self._thread = threading.Thread(target=_cleanup, daemon=True)
                self._thread.start()

        except Exception as e:
            print(f"[watch] watchdog error: {e}, falling back to polling")
            self._start_polling(block)


# ---------------------------------------------------------------------------
# Compiler integration
# ---------------------------------------------------------------------------

def _run_lateralus(path: Path, mode: str = "run") -> int:
    """Invoke the LATERALUS compiler/runner on a file."""
    cmd = [sys.executable, "-m", "lateralus_lang", mode, str(path)]
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode


class CompileOnChange:
    """
    Recompiles (and optionally runs) a LATERALUS file whenever it changes.

    Usage:
        coc = CompileOnChange(watcher, mode="run")
        coc.install()
    """

    def __init__(self, watcher: FileWatcher, mode: str = "check",
                 entry: Optional[Path] = None, quiet: bool = False) -> None:
        self._watcher = watcher
        self._mode = mode     # "run" | "check" | "build"
        self._entry = entry   # if set, always run this file; else use changed file
        self._quiet = quiet
        self._last_run: dict[str, float] = {}
        self._debounce = 0.3  # seconds

    def install(self) -> "CompileOnChange":
        self._watcher.on_change(self._handle)
        return self

    def _handle(self, event: FileChangeEvent) -> None:
        if event.kind == ChangeKind.DELETED:
            return

        path = event.path
        now = time.monotonic()
        key = str(path)

        # Debounce: skip if we ran this file within the last 0.3s
        if now - self._last_run.get(key, 0.0) < self._debounce:
            return
        self._last_run[key] = now

        target = self._entry or path
        if not self._quiet:
            print(f"\n[watch] {event.kind}: {path.name}  →  {self._mode} {target.name}")
            print("-" * 50)

        rc = _run_lateralus(target, self._mode)

        if not self._quiet:
            status = "✓ OK" if rc == 0 else f"✗ exit {rc}"
            print(f"[watch] {status}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def watch_cli(args: list[str]) -> None:
    """
    CLI entry for `lateralus watch`:
        lateralus watch <path> [--run] [--check] [--build] [--entry FILE] [-q]
    """
    import argparse

    ap = argparse.ArgumentParser(prog="lateralus watch",
                                 description="Watch .ltl files and recompile on change")
    ap.add_argument("path", help="Directory or file to watch")
    ap.add_argument("--run",   action="store_true", help="Run file on change")
    ap.add_argument("--check", action="store_true", help="Type-check on change (default)")
    ap.add_argument("--build", action="store_true", help="Build bytecode on change")
    ap.add_argument("--entry", help="Always run this entry file (instead of changed file)")
    ap.add_argument("-q", "--quiet", action="store_true", help="Suppress output")
    ap.add_argument("--interval", type=float, default=0.5, help="Poll interval seconds")

    opts = ap.parse_args(args)

    if opts.run:
        mode = "run"
    elif opts.build:
        mode = "build"
    else:
        mode = "check"

    entry = Path(opts.entry) if opts.entry else None

    watcher = FileWatcher(opts.path, interval=opts.interval)
    CompileOnChange(watcher, mode=mode, entry=entry, quiet=opts.quiet).install()
    watcher.start(block=True)


def get_watch_builtins() -> dict:
    return {
        "FileWatcher":     FileWatcher,
        "FileChangeEvent": FileChangeEvent,
        "ChangeKind":      ChangeKind,
        "CompileOnChange": CompileOnChange,
    }
