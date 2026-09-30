"""Arg completers for quickie CLI."""

from __future__ import annotations

import typing
import collections.abc

from quickie.completion.base import BaseCompleter
from quickie.errors import QuickieError
from quickie import app


class TaskCompleter(BaseCompleter):
    """For auto-completing task names. Used internally by the CLI."""

    def __init__(self, extra: collections.abc.Mapping[str, str] | None = None):
        self.extra = dict(extra or {})

    @typing.override
    def complete(self, *, prefix: str, **_):
        try:
            completions = {
                key: help_text
                for key, help_text in self.extra.items()
                if key.startswith(prefix)
            }
            # Fast path: use disk cache if available
            if app.cached_task_names is not None:
                completions.update(
                    {
                        key: entry["help"]
                        for key, entry in app.cached_task_names.items()
                        if key.startswith(prefix)
                    }
                )
                return completions
            # Slow path: iterate full task objects
            completions.update(
                {
                    key: task.get_short_help()
                    for key, task in app.tasks.items()
                    if key.startswith(prefix)
                }
            )
            return completions
        except (QuickieError, ValueError):
            return {}
