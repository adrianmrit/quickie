"""Arg completers for quickie CLI."""

from __future__ import annotations

import typing

from quickie.completion.base import BaseCompleter
from quickie.errors import QuickieError

if typing.TYPE_CHECKING:
    from quickie.cli import Main as TMain  # pragma: no cover


class TaskCompleter(BaseCompleter):
    """For auto-completing task names. Used internally by the CLI."""

    @typing.override
    def __init__(self, main: TMain):
        self.main = main

    @typing.override
    def complete(self, *, prefix, **_):
        try:
            return {
                key: task._meta.short_help or ""
                for key, task in self.main.tasks_namespace.items()
                if key.startswith(prefix)
            }
        except QuickieError:
            pass
