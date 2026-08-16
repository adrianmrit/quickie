"""Arg completers for quickie CLI."""

from __future__ import annotations

import typing

from quickie.completion.base import BaseCompleter
from quickie.errors import QuickieError
from quickie import app


class TaskCompleter(BaseCompleter):
    """For auto-completing task names. Used internally by the CLI."""

    @typing.override
    def complete(self, *, prefix: str, **_):
        try:
            # Fast path: use disk cache if available
            if app.cached_task_names is not None:
                return {
                    key: entry["help"]
                    for key, entry in app.cached_task_names.items()
                    if key.startswith(prefix)
                }
            # Slow path: iterate full task objects
            return {
                key: task.get_short_help()
                for key, task in app.tasks.items()
                if key.startswith(prefix)
            }
        except (QuickieError, ValueError):
            return {}
