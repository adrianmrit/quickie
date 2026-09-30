"""The ``:run`` command — run a named task."""

from __future__ import annotations

import typing
from argparse import REMAINDER, ArgumentParser
import os
from contextlib import redirect_stderr
from io import StringIO

import argcomplete
from argcomplete.completers import SuppressCompleter

from quickie import app
from quickie.commands.base import CliCommand
from quickie.completion._internal import TaskCompleter
from quickie.errors import QuickieError


def _autocomplete_task(parser: ArgumentParser, args: list[str]) -> None:
    """Complete a command's task and, when known, its task arguments."""
    with redirect_stderr(StringIO()):
        try:
            namespace, _ = parser.parse_known_args(args)
        except SystemExit:
            namespace = None
    if not getattr(namespace, "task", None):
        if app.cached_task_names is None:
            try:
                app.load_tasks()
            except QuickieError:
                pass
        argcomplete.autocomplete(parser)
        return
    assert namespace is not None
    task_name = namespace.task

    try:
        app._try_load_task_cache()
        cache_entry = (app.cached_task_names or {}).get(task_name)
        cached_args = cache_entry.get("args") if cache_entry else None
        if cached_args is not None and not cached_args.get(
            "has_unknown_completers", True
        ):
            from quickie._cache import rebuild_parser

            task_parser = rebuild_parser(task_name, cached_args)
        else:
            try:
                app.load_tasks()
            except QuickieError:
                pass
            task_parser = app.tasks[task_name].parser
    except (KeyError, QuickieError):
        argcomplete.autocomplete(parser)
        return

    task_index = len(args) - len(namespace.args) - 1
    if args[task_index] == "--":
        task_index -= 1
    os.environ["_ARGCOMPLETE"] = str(int(os.environ["_ARGCOMPLETE"]) + task_index + 1)
    argcomplete.autocomplete(task_parser)


class RunCommand(CliCommand):
    """Run a named task with optional arguments."""

    @typing.override
    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "task", nargs="?", metavar="TASK", help="Name of the task to run"
        ).completer = TaskCompleter()  # type: ignore
        parser.add_argument(
            "args", nargs=REMAINDER, metavar="ARGS", help="Arguments passed to the task"
        ).completer = SuppressCompleter()  # type: ignore

    @typing.override
    def autocomplete(self, parser: ArgumentParser, args: list[str]) -> None:
        _autocomplete_task(parser, args)

    @typing.override
    def execute(self, namespace: object) -> None:
        ns = typing.cast("_RunNamespace", namespace)
        task = app.tasks[ns.task]
        task.parse_and_run(ns.args)


class _RunNamespace:
    """Minimal type hint for the ``:run`` namespace."""

    task: str
    args: list[str]
