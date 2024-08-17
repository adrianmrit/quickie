"""Arg completers for quickie CLI."""

from __future__ import annotations

import typing

from quickie.completion.base import BaseCompleter
from quickie.errors import QuickieError

if typing.TYPE_CHECKING:
    from quickie._cli import Main as TMain  # pragma: no cover


class TaskCompleter(BaseCompleter):
    """For auto-completing task names. Used internally by the CLI."""

    @typing.override
    def __init__(self, main: TMain):
        self.main = main

    @typing.override
    def complete(self, *, prefix: str, **_):
        try:
            return {
                key: task.get_short_help()
                for key, task in self.main.root_namespace.items()
                if key.startswith(prefix)
            }
        except QuickieError:
            pass
