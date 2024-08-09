"""Arg completers for task-mom CLI."""

from __future__ import annotations

import typing

from task_mom.completion.base import BaseCompleter
from task_mom.errors import MomError

if typing.TYPE_CHECKING:
    from task_mom.cli import Main as TMain  # pragma: no cover


class TaskCompleter(BaseCompleter):
    """For auto-completing task names. Used internally by the CLI."""

    @typing.override
    def __init__(self, main: TMain):
        self.main = main

    @typing.override
    def complete(self, *, prefix, parsed_args, **_):
        try:
            self.main.load_tasks_from_namespace(parsed_args)
            return {
                key: task._meta.short_help or ""
                for key, task in self.main.tasks_namespace.items()
                if key.startswith(prefix)
            }
        except MomError:
            pass
