"""File watcher for watch mode.

Uses watchdog's OS-native Observer to detect file changes with debounce.
"""

from __future__ import annotations

import logging
import os
import threading
import time
import typing
from pathlib import Path

from watchdog.events import FileSystemEvent, PatternMatchingEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

logger = logging.getLogger("quickie")

DEFAULT_DEBOUNCE: float = 0.5
"""Seconds to wait after a change before reporting it.

Prevents rapid re-runs when an IDE auto-formats multiple files on save.
"""

_DEFAULT_EXCLUDE: list[str] = [
    "**/.git/**",
    "**/__pycache__/**",
    "**/*.pyc",
    "**/.quickie_cache/**",
]


class _ChangeHandler(PatternMatchingEventHandler):
    """Accumulates file change events in a thread-safe set."""

    def __init__(self, watcher: FileWatcher):
        super().__init__(
            patterns=watcher._patterns,
            ignore_patterns=watcher._ignore_patterns,
            # Quickie reruns for file changes, not directory metadata events.
            ignore_directories=True,
        )
        self._watcher = watcher

    @typing.override
    def on_any_event(self, event: FileSystemEvent) -> None:
        path = str(event.src_path)
        if self._watcher._is_ignored(path):
            return
        with self._watcher._condition:
            self._watcher._changed_paths.add(path)
            self._watcher._last_change_time = time.monotonic()
            self._watcher._changed.set()
            self._watcher._condition.notify_all()


class FileWatcher:
    """Watches files for changes using watchdog's OS-native Observer.

    The observer automatically selects the best backend for the current OS
    (FSEvents on macOS, inotify on Linux, etc.).
    """

    def __init__(
        self,
        watch_paths: list[str],
        patterns: list[str] | None = None,
        ignore_paths: list[str] | None = None,
        ignore_patterns: list[str] | None = None,
        wd: str | Path | None = None,
        debounce: float = DEFAULT_DEBOUNCE,
        recursive: bool = False,
    ):
        """Initialize the file watcher.

        :param watch_paths: Paths to watch. Relative entries are resolved
            against *wd*; absolute entries are used as-is.
        :param patterns: Watchdog wildcard patterns for included file events.
        :param ignore_paths: Paths to be ignored.
        :param ignore_patterns: Watchdog wildcard patterns for ignored events.
        :param wd: Working directory to resolve relative paths against.
        :param debounce: Seconds to wait after a change before reporting it.
        :param recursive: Whether watched directories should be observed
            recursively.
        """
        self._watch_paths = watch_paths
        self._patterns = patterns or ["*"]
        self._ignore_patterns = ignore_patterns or list(_DEFAULT_EXCLUDE)
        self._wd = (Path(wd) if wd else Path.cwd()).resolve()
        self._ignore_paths = tuple(
            (self._wd / path if not Path(path).is_absolute() else Path(path)).resolve()
            for path in (ignore_paths or [])
        )
        self._debounce = debounce
        self._recursive = recursive

        self._watch_dirs: tuple[Path, ...] | None = None
        self._observer: BaseObserver | None = None
        self._changed = threading.Event()
        self._last_change_time: float = 0.0
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._stopped = threading.Event()
        self._changed_paths: set[str] = set()

    def _is_ignored(self, path: str) -> bool:
        """Check if a path is below an ignored directory path."""
        candidate = Path(path).resolve()
        for ignored in self._ignore_paths:
            if candidate == ignored or candidate.is_relative_to(ignored):
                return True
        return False

    @property
    def watch_dirs(self) -> tuple[Path, ...]:
        """The directories being observed, resolved on first access."""
        if self._watch_dirs is None:
            self._watch_dirs = tuple(self._resolve_watch_dirs())
        return self._watch_dirs

    def _resolve_watch_dirs(self) -> list[Path]:
        """Resolve watch paths to actual directories to observe."""
        dirs: list[Path] = []
        seen: set[Path] = set()
        for path in self._watch_paths:
            resolved = path if os.path.isabs(path) else os.path.join(self._wd, path)
            directory = Path(resolved).resolve()
            if directory.is_dir() and directory not in seen:
                dirs.append(directory)
                seen.add(directory)
        if not dirs:
            # Fallback to working directory
            dirs.append(self._wd)
        return dirs

    def start(self) -> None:
        """Start watching for file changes."""
        if self._observer is not None:
            return

        self._stopped.clear()
        self._observer = Observer()
        handler = _ChangeHandler(self)

        for d in self.watch_dirs:
            logger.debug(f"Watching directory: {d}")
            self._observer.schedule(handler, str(d), recursive=self._recursive)

        self._observer.start()

    def stop(self) -> None:
        """Stop watching for file changes."""
        self._stopped.set()
        with self._condition:
            self._condition.notify_all()
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

    def wait_for_changes(self) -> bool:
        """Wait until debounced changes are ready or the watcher is stopped.

        :returns: ``True`` when changes are ready, or ``False`` after
            :meth:`stop` has been called.
        """
        with self._condition:
            while not self._stopped.is_set():
                if self._changed.is_set():
                    remaining = self._debounce - (
                        time.monotonic() - self._last_change_time
                    )
                    if remaining <= 0:
                        return True
                else:
                    remaining = None
                self._condition.wait(timeout=remaining)
        return False

    def reset(self) -> None:
        """Clear the change state after a task has been re-run."""
        with self._lock:
            self._changed_paths.clear()
            self._changed.clear()

    def changed_paths(self) -> list[str]:
        """Return paths accumulated since the last reset."""
        with self._lock:
            return sorted(self._changed_paths)
