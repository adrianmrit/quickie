"""File watcher for watch mode.

Uses watchdog's OS-native Observer to detect file changes with debounce.
"""

from __future__ import annotations

import fnmatch
import logging
import os
import threading
import time
import typing
from pathlib import Path

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

logger = logging.getLogger("quickie")

DEFAULT_DEBOUNCE: float = 0.5
"""Seconds to wait after a change before reporting it.

Prevents rapid re-runs when an IDE auto-formats multiple files on save.
"""

DEFAULT_POLL_INTERVAL: float = 0.25
"""Seconds between polls of the change state.

Must be shorter than ``DEFAULT_DEBOUNCE`` for responsive detection.
"""

_DEFAULT_EXCLUDE: list[str] = [
    ".git",
    "__pycache__",
    "*.pyc",
    ".quickie_cache",
    "tmp",
]


class _ChangeHandler(FileSystemEventHandler):
    """Accumulates file change events in a thread-safe set."""

    def __init__(self, watcher: FileWatcher):
        super().__init__()
        self._watcher = watcher

    @typing.override
    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = str(event.src_path)
        if self._watcher._is_excluded(path):
            return
        with self._watcher._lock:
            self._watcher._changed_paths.add(path)
            self._watcher._last_change_time = time.monotonic()
            self._watcher._changed.set()


class FileWatcher:
    """Watches files for changes using watchdog's OS-native Observer.

    The observer automatically selects the best backend for the current OS
    (FSEvents on macOS, inotify on Linux, etc.).

    :param watch_paths: List of glob patterns or directories to watch.
    :param exclude: List of glob patterns or directories to exclude.
    :param wd: Working directory to resolve paths against.
    :param debounce: Seconds to wait after a change before reporting it.
    """

    def __init__(
        self,
        watch_paths: list[str],
        exclude: list[str] | None = None,
        wd: str | Path | None = None,
        debounce: float = DEFAULT_DEBOUNCE,
    ):
        self._watch_paths = watch_paths
        self._exclude = exclude or list(_DEFAULT_EXCLUDE)
        self._wd = Path(wd) if wd else Path.cwd()
        self._debounce = debounce

        self._observer: BaseObserver | None = None
        self._changed = threading.Event()
        self._last_change_time: float = 0.0
        self._lock = threading.Lock()
        self._changed_paths: set[str] = set()

    def _is_excluded(self, path: str) -> bool:
        """Check if a path matches any exclude pattern."""
        name = os.path.basename(path)
        # Split path into components for directory matching
        parts = Path(path).parts
        for pattern in self._exclude:
            # Check against basename (for glob patterns like *.pyc)
            if fnmatch.fnmatch(name, pattern):
                return True
            # Check against full path (for patterns like .git)
            if fnmatch.fnmatch(path, pattern):
                return True
            # Check if pattern matches any path component (for directory names)
            if any(fnmatch.fnmatch(part, pattern) for part in parts):
                return True
        return False

    def _resolve_watch_dirs(self) -> list[Path]:
        """Resolve watch paths to actual directories to observe."""
        dirs: list[Path] = []
        for pattern in self._watch_paths:
            p = self._wd / pattern
            if p.is_dir():
                dirs.append(p)
            else:
                # Try glob expansion
                matches = list(self._wd.glob(pattern))
                for m in matches:
                    if m.is_dir() and m not in dirs:
                        dirs.append(m)
        if not dirs:
            # Fallback to working directory
            dirs.append(self._wd)
        return dirs

    def start(self) -> None:
        """Start watching for file changes."""
        if self._observer is not None:
            return

        self._observer = Observer()
        handler = _ChangeHandler(self)
        dirs = self._resolve_watch_dirs()

        for d in dirs:
            logger.debug(f"Watching directory: {d}")
            self._observer.schedule(handler, str(d), recursive=True)

        self._observer.start()

    def stop(self) -> None:
        """Stop watching for file changes."""
        if self._observer is not None:
            self._observer.stop()
            self._observer.join()
            self._observer = None

    def has_changes(self) -> bool:
        """Check if any file changes have been detected (with debounce).

        Returns True only if changes were detected AND the debounce period
        has elapsed since the last change.

        :returns: True if changes are ready to be acted on.
        """
        if not self._changed.is_set():
            return False

        with self._lock:
            elapsed = time.monotonic() - self._last_change_time
            if elapsed >= self._debounce:
                return True
        return False

    def reset(self) -> None:
        """Clear the change state after a task has been re-run."""
        with self._lock:
            self._changed_paths.clear()
            self._changed.clear()
