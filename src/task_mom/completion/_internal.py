"""Arg completers for task-mom CLI."""

from __future__ import annotations

import argparse
import typing

import argcomplete

from task_mom.completion.base import BaseCompleter, PathCompleter
from task_mom.errors import MomError
from task_mom.namespace import global_namespace

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
                for key, task in global_namespace.items()
                if key.startswith(prefix)
            }
        except MomError:
            pass


class ArgsCompleter(PathCompleter):
    """For auto-completing task arguments. Used internally by the CLI."""

    @typing.override
    def __init__(self, main: TMain):
        self.main = main

    def get_task_args(
        self, prefix: str, parsed_args: argparse.Namespace
    ) -> typing.Generator[tuple[str, str], None, None]:
        try:
            try:
                self.main.load_tasks_from_namespace(parsed_args)
                task = self.main.get_task(parsed_args.task)
            except MomError:
                return
            for action in task.parser._actions:
                if action.option_strings:
                    for option in action.option_strings:
                        if option.startswith(prefix):
                            yield option, action.help
        except Exception as e:
            argcomplete.warn("Autocompletion failed with error:", e)

    @typing.override
    def complete(self, *, prefix, action, parser, parsed_args):
        if not parsed_args.task:
            return {}
        options = {}
        options.update(self.get_task_args(prefix, parsed_args))
        for name in super().complete(prefix, action, parser, parsed_args):
            if name not in options:
                options[name] = ""
        return options
