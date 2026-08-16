"""Disk cache for task metadata to speed up autocomplete.

The cache lives in a ``.quickie_cache/`` directory inside the tasks
directory.  An inner ``.gitignore`` is created automatically so that
users never accidentally commit cached data.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quickie.tasks import Task

_CACHE_DIR_NAME = ".quickie_cache"
_CACHE_FILE_NAME = "task_names.json"
_GITIGNORE_CONTENT = "*\n"

# Completers we can recreate from cache (stateless, no constructor args).
_REBUILDABLE_COMPLETERS: frozenset[str] = frozenset(
    {"PathCompleter", "PytestCompleter"}
)


class TaskCache:
    """Disk cache mapping task names to their help text and arg metadata."""

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _cache_dir(tasks_path: Path) -> Path:
        return tasks_path / _CACHE_DIR_NAME

    @staticmethod
    def _cache_file(tasks_path: Path) -> Path:
        return TaskCache._cache_dir(tasks_path) / _CACHE_FILE_NAME

    @staticmethod
    def _gitignore_file(tasks_path: Path) -> Path:
        return TaskCache._cache_dir(tasks_path) / ".gitignore"

    # ------------------------------------------------------------------
    # Cache dir management
    # ------------------------------------------------------------------

    @staticmethod
    def _ensure_cache_dir(tasks_path: Path) -> None:
        """Create the cache directory and ``.gitignore`` if missing."""
        cache_dir = TaskCache._cache_dir(tasks_path)
        cache_dir.mkdir(parents=True, exist_ok=True)

        gitignore = TaskCache._gitignore_file(tasks_path)
        if not gitignore.exists():
            gitignore.write_text(_GITIGNORE_CONTENT)

    # ------------------------------------------------------------------
    # Save / load
    # ------------------------------------------------------------------

    @staticmethod
    def save(tasks_path: Path, tasks: dict[str, dict], version: str) -> None:
        """Write task metadata to the disk cache.

        :param tasks_path: Root path of the tasks module.
        :param tasks: Mapping of ``{task_name: {"help": ..., "args": ...}}``.
        :param version: Current quickie version string.
        """
        TaskCache._ensure_cache_dir(tasks_path)
        data = {"_version": version, "tasks": tasks}
        TaskCache._cache_file(tasks_path).write_text(
            json.dumps(data, indent=None) + "\n"
        )

    @staticmethod
    def load(tasks_path: Path, version: str) -> dict | None:
        """Load cached task metadata if the cache is still valid.

        Returns ``None`` when the cache is missing, corrupt, or stale.

        :param tasks_path: Root path of the tasks module.
        :param version: Current quickie version string (for invalidation).
        """
        cache_file = TaskCache._cache_file(tasks_path)
        if not cache_file.exists():
            return None

        cache_mtime = cache_file.stat().st_mtime
        if TaskCache._is_stale(tasks_path, cache_mtime):
            return None

        try:
            data = json.loads(cache_file.read_text())
        except (json.JSONDecodeError, OSError):
            return None

        if data.get("_version") != version:
            return None

        return data.get("tasks")

    # ------------------------------------------------------------------
    # Staleness
    # ------------------------------------------------------------------

    @staticmethod
    def _is_stale(tasks_path: Path, cache_mtime: float) -> bool:
        """Return `True` if any `.py` file is newer than *cache_mtime*."""
        try:
            for file_path in tasks_path.rglob("*.py"):
                # Skip hidden directories like .quickie_cache
                if any(part.startswith(".") for part in file_path.parts):
                    continue

                if file_path.stat().st_mtime > cache_mtime:
                    return True

        except OSError:
            return True

        return False


# ------------------------------------------------------------------
# Cache population helpers
# ------------------------------------------------------------------


def _detect_completer_type(action: argparse.Action) -> str | None:
    """Return the completer type name for *action*, or ``None``."""
    completer = getattr(action, "completer", None)
    if completer is None:
        return None
    return type(completer).__name__


def build_cache_entry(task: Task) -> dict:
    """Build a cache-entry dict for a single task.

    Returns ``{"help": ..., "args": ...}`` where *args* is either ``None``
    (no arguments) or a dict with ``schema`` and ``has_unknown_completers``.
    """
    schema = task._get_args_schema()

    # Build a lookup by dest so we can enrich in a single pass
    schema_by_dest: dict[str, dict] = {e["dest"]: e for e in schema}

    # Enrich schema with completer_type and detect unknown completers
    has_unknown = False
    for action in task.parser._actions:
        if isinstance(action, argparse._HelpAction):
            continue
        entry = schema_by_dest.get(action.dest)
        if entry is not None:
            completer_type = _detect_completer_type(action)
            entry["completer_type"] = completer_type
            if (
                completer_type is not None
                and completer_type not in _REBUILDABLE_COMPLETERS
            ):
                has_unknown = True

    if not schema:
        args = None
    else:
        args = {"schema": schema, "has_unknown_completers": has_unknown}

    return {"help": task.get_short_help(), "args": args}


# ------------------------------------------------------------------
# Parser rebuild (for arg completion from cache)
# ------------------------------------------------------------------


def rebuild_parser(task_name: str, cached_args: dict) -> argparse.ArgumentParser:
    """Rebuild a lightweight ``ArgumentParser`` from cached arg metadata.

    :param task_name: Name of the task (used as ``prog``).
    :param cached_args: The ``args`` dict from the cache (must not be ``None``).
    :returns: A parser with arguments and known completers reattached.
    """
    parser = argparse.ArgumentParser(prog=task_name)

    for entry in cached_args["schema"]:
        flags = entry["flags"]
        kwargs: dict = {}

        # Only the fields needed for argcomplete completion.
        if entry.get("choices") is not None:
            kwargs["choices"] = entry["choices"]
        if entry.get("nargs") is not None:
            kwargs["nargs"] = entry["nargs"]

        action = parser.add_argument(*flags, **kwargs)

        # Reattach known completers
        completer_type = entry.get("completer_type")
        if completer_type == "PathCompleter":
            from quickie.completion import PathCompleter

            setattr(action, "completer", PathCompleter())
        elif completer_type == "PytestCompleter":
            from quickie.completion.python import PytestCompleter

            setattr(action, "completer", PytestCompleter())

    return parser
