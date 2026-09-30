"""The ``:watch`` command — watch files and re-run a task."""

from __future__ import annotations

import typing

from argparse import REMAINDER, ArgumentParser
from argcomplete.completers import SuppressCompleter

from quickie import app
from quickie.commands.base import CliCommand
from quickie.completion._internal import TaskCompleter
from quickie.commands.run import _autocomplete_task


def _split_watch_values(values: list[str]) -> list[str]:
    """Split watchmedo-style semicolon-separated values."""
    return [part for value in values for part in value.split(";") if part]


class WatchCommand(CliCommand):
    """Run a task and re-run it when watched files change."""

    @typing.override
    def configure_parser(self, parser: ArgumentParser) -> None:
        for name in ("paths", "ignore_paths", "patterns", "ignore_patterns"):
            parser.add_argument(f"--{name.replace('_', '-')}", action="append")
        parser.add_argument("--recursive", action="store_true", default=None)
        parser.add_argument("--debounce", type=float, default=None)
        parser.add_argument(
            "task", metavar="TASK", help="Name of the task to watch"
        ).completer = TaskCompleter()  # type: ignore
        parser.add_argument(
            "args", nargs=REMAINDER, metavar="ARGS", help="Arguments passed to the task"
        ).completer = SuppressCompleter()  # type: ignore

    @typing.override
    def autocomplete(self, parser: ArgumentParser, args: list[str]) -> None:
        _autocomplete_task(parser, args)

    @typing.override
    def execute(self, namespace: object) -> None:
        from quickie._watcher import (
            FileWatcher,
            DEFAULT_DEBOUNCE,
            _DEFAULT_EXCLUDE,
        )

        ns = typing.cast("_WatchNamespace", namespace)

        task = app.tasks[ns.task]
        extra_args, task_kwargs = task.parse_args(
            parser=task.parser,
            args=ns.args,
            extra_args=task.extra_args,
        )
        config = task.get_watch_config(extra_args, **task_kwargs)

        watch_paths = (
            ns.paths if ns.paths is not None else (config["watch_paths"] or ["."])
        )
        watch_ignore_paths = (
            ns.ignore_paths
            if ns.ignore_paths is not None
            else config["watch_ignore_paths"]
        )
        watch_patterns = (
            _split_watch_values(ns.patterns)
            if ns.patterns is not None
            else config["watch_patterns"]
        )
        watch_ignore_patterns = (
            _split_watch_values(ns.ignore_patterns)
            if ns.ignore_patterns is not None
            else config["watch_ignore_patterns"]
        )
        debounce = ns.debounce if ns.debounce is not None else config["watch_debounce"]
        recursive = (
            ns.recursive if ns.recursive is not None else config["watch_recursive"]
        )

        # Final fallback to module-level defaults
        if debounce is None:
            debounce = DEFAULT_DEBOUNCE

        if recursive is None:
            recursive = False

        wd = config["wd"]
        ignore_paths = [*(watch_ignore_paths or []), str(app.tmp_path)]
        ignore_patterns = list(watch_ignore_patterns or _DEFAULT_EXCLUDE)

        watcher = FileWatcher(
            watch_paths=watch_paths,
            patterns=watch_patterns,
            ignore_paths=ignore_paths,
            ignore_patterns=ignore_patterns,
            wd=wd,
            debounce=debounce,
            recursive=recursive,
        )

        # Print watch summary
        app.console.print(
            "[bold cyan]Watching for changes...[/bold cyan] (Ctrl+C to stop)"
        )
        app.console.print(f"  Task: [bold yellow]{ns.task}[/bold yellow]")
        app.console.print(f"  Paths: [dim]{', '.join(watch_paths)}[/dim]")
        if watch_ignore_paths:
            app.console.print(
                f"  Ignore paths: [dim]{', '.join(watch_ignore_paths)}[/dim]"
            )
        if watch_patterns:
            app.console.print(f"  Patterns: [dim]{'; '.join(watch_patterns)}[/dim]")
        if watch_ignore_patterns:
            app.console.print(
                f"  Ignore patterns: [dim]{'; '.join(watch_ignore_patterns)}[/dim]"
            )
        app.console.print()

        try:
            # Run once before observing, so task-generated file events do not
            # become an immediate watch trigger.
            app.console.print(f"[bold green]Running {ns.task}...[/bold green]\n")
            task.parse_and_run(ns.args)
            app.console.print()

            watcher.start()

            while watcher.wait_for_changes():
                changed_paths = watcher.changed_paths()
                msg = f"Changes detected, re-running {ns.task}..."
                app.console.print(f"[bold yellow]{msg}[/bold yellow]")
                for path in changed_paths:
                    app.console.print(f"  [dim]{path}[/dim]")
                app.console.print()
                watcher.reset()
                task.parse_and_run(ns.args)
                app.console.print()
        except KeyboardInterrupt:
            app.console.print("\n[bold red]Watching stopped.[/bold red]")
        finally:
            watcher.stop()


class _WatchNamespace:
    """Minimal type hint for the ``:watch`` namespace."""

    task: str
    args: list[str]
    paths: list[str] | None
    ignore_paths: list[str] | None
    patterns: list[str] | None
    ignore_patterns: list[str] | None
    debounce: float | None
    recursive: bool | None
