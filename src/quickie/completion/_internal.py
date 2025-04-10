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
            return {
                key: task.get_short_help()
                for key, task in app.tasks.items()
                if key.startswith(prefix)
            }
        except QuickieError:
            pass
