"""The CLI entry of quickie."""

import json
import os
import sys
import time
from functools import wraps

import argcomplete

import quickie
from quickie import app
from quickie._argparser import AppArgumentParser
from quickie._init import init
from quickie._launcher import Launcher
from quickie.errors import QuickieError, Skip, Stop

_parser = AppArgumentParser()


def _clean_exit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            print("Exiting due to KeyboardInterrupt.")
            sys.exit(1)

    return wrapper


@_clean_exit
def main(argv=None, *, raise_error=False, global_=False):
    """Run the CLI."""
    from rich import traceback

    traceback.install(suppress=[quickie])

    if argv is None:
        argv = sys.argv[1:]

    main_obj = Main(argv=argv, global_=global_)
    app.set_verbosity(main_obj.namespace.verbosity)

    launcher = Launcher()
    if (
        not global_
        and not main_obj.namespace.use_global
        and not launcher.is_in_recursion()
    ):
        try:
            app.logger.debug("Attempting launcher discovery...")
            exit_code = launcher.launch(argv)
            sys.exit(exit_code)
        except QuickieError as e:
            app.logger.debug(f"Launcher discovery failed: {e}")
        except Exception as e:
            app.logger.debug(f"Unexpected error in launcher: {e}")

    if os.environ.get("_ARGCOMPLETE"):
        main_obj.handle_autocomplete()
        return  # handle_autocomplete calls sys.exit

    try:
        main_obj()
    except Stop as e:
        if e.message:
            app.logger.info(f"Stopping: [info]{e.message}[/info]")
        else:
            app.logger.info(f"Stopping because {Stop.__name__} exception was raised.")
        sys.exit(e.exit_code)
    except Skip as e:
        if e.message:
            app.logger.info(f"Skipping: [info]{e.message}[/info]")
        else:
            app.logger.info(f"Skipping because {Skip.__name__} exception was raised.")
    except QuickieError as e:
        if raise_error:
            raise e
        app.logger.error(f"[error]{e}[/error]")
        sys.exit(e.exit_code)


class Main:
    """Represents the CLI entry of quickie."""

    def __init__(self, *, argv=None, global_=False):  # noqa: PLR0913
        """Initialize the CLI."""
        if argv is None:
            argv = sys.argv[1:]
        self.argv = argv
        self.global_ = global_
        self.namespace = _parser.parse_args(argv)

    def handle_autocomplete(self):
        """Handle argcomplete tab completion. Calls sys.exit."""
        arg_complete_val = os.environ["_ARGCOMPLETE"]
        comp_line = os.environ["COMP_LINE"]
        comp_point = int(os.environ["COMP_POINT"])

        (_, _, _, comp_words, _) = argcomplete.lexers.split_line(comp_line, comp_point)

        # _ARGCOMPLETE is set by the shell script to tell us where comp_words
        # should start, based on what we're completing.
        # we ignore the program name, hence no -1
        start = int(arg_complete_val)
        args = comp_words[start:]
        namespace = _parser.parse_args(args)

        app.set_verbosity(namespace.verbosity)
        app.set_log_file(namespace.log_file)
        use_global = self.global_ or namespace.use_global
        if not use_global and namespace.module:
            app.set_project_path(namespace.module)
        app.set_use_global(use_global)

        # --- Fast path: try the disk cache ---
        app._try_load_task_cache()
        cache_available = app.cached_task_names is not None

        if not namespace.task:
            # Task-name completion — cache is sufficient
            if not cache_available:
                try:
                    app.load_tasks()
                except QuickieError:
                    pass
            parser = _parser
        else:
            # Task-argument completion — try cache first
            task_cache_entry = (
                app.cached_task_names.get(namespace.task) if cache_available else None
            )
            cached_args = task_cache_entry.get("args") if task_cache_entry else None

            if cached_args is not None and not cached_args.get(
                "has_unknown_completers", True
            ):
                # Rebuild a lightweight parser from cached metadata
                from quickie._cache import rebuild_parser

                os.environ["_ARGCOMPLETE"] = str(args.index(namespace.task))
                parser = rebuild_parser(namespace.task, cached_args)
            else:
                # Fall back to full import
                try:
                    app.load_tasks()
                except QuickieError:
                    pass
                try:
                    task = self.get_task(namespace.task)
                except (QuickieError, KeyError):
                    parser = _parser
                else:
                    os.environ["_ARGCOMPLETE"] = str(args.index(namespace.task))
                    parser = task.parser

        argcomplete.autocomplete(parser)
        sys.exit(0)

    def __call__(self):
        """Run the CLI."""
        namespace = self.namespace

        app.set_log_file(namespace.log_file)
        use_global = self.global_ or namespace.use_global
        if not use_global and namespace.module:
            app.set_project_path(namespace.module)
        app.set_use_global(use_global)

        # Handle --list-json before any Rich/logger output so that stdout
        # contains only the raw JSON (used by qk-mcp to enumerate tasks).
        if namespace.list_json:
            app.load_tasks()
            self.list_tasks_json(namespace.list_filter)
            _parser.exit()
            return

        app.logger.info(f"Running quickie {quickie.__version__}")
        if namespace.init:
            init(namespace.init)
        elif namespace.suggest_auto_completion:
            if namespace.suggest_auto_completion == "bash":
                self.suggest_autocompletion_bash()
            elif namespace.suggest_auto_completion == "zsh":
                self.suggest_autocompletion_zsh()
        elif namespace.list:
            app.load_tasks()
            self.list_tasks(namespace.list_filter)
        elif namespace.task is not None:
            app.load_tasks()
            if namespace.watch:
                self.watch_task(
                    task_name=namespace.task,
                    args=namespace.args,
                    watch_paths=namespace.watch_paths,
                    watch_exclude=namespace.watch_exclude,
                    debounce=namespace.watch_debounce,
                    poll_interval=namespace.watch_interval,
                )
            else:
                self.run_task(
                    task_name=namespace.task,
                    args=namespace.args,
                )
        elif namespace.watch:
            app.console.print("[error]--watch requires a task to run.[/error]")
            _parser.exit(1)
        else:
            from rich.text import Text

            app.console.print(Text.from_ansi(self.get_usage()))
        _parser.exit()

    def suggest_autocompletion_bash(self):
        """Suggest autocompletion for bash."""
        program = os.path.basename(sys.argv[0])
        app.console.print("Add the following to ~/.bashrc or ~/.bash_profile:")
        app.console.print(
            f'eval "$(register-python-argcomplete {program})"',
            style="bold green",
        )

    def suggest_autocompletion_zsh(self):
        """Suggest autocompletion for zsh."""
        program = os.path.basename(sys.argv[0])
        app.console.print("Add the following to ~/.zshrc:")
        app.console.print(
            f'eval "$(register-python-argcomplete {program})"',
            style="bold green",
        )

    @staticmethod
    def _task_list_entries(filter_text: str | None = None) -> list[dict]:
        """Build task metadata grouped by the namespace they invoke from."""
        cwd = os.getcwd()
        grouped: dict[int, tuple[quickie.Task, list[str]]] = {}
        for invocation_name, task in app.tasks.items():
            grouped.setdefault(id(task), (task, []))[1].append(invocation_name)

        entries = []
        for task, invocation_names in grouped.values():
            entry = task.to_info_dict(cwd)
            if task.name in invocation_names:
                entry["name"] = task.name
            else:
                canonical_paths = [
                    name for name in invocation_names if name.endswith(f":{task.name}")
                ]
                entry["name"] = min(canonical_paths, key=lambda name: name.split(":"))
            entry["aliases"] = sorted(
                name for name in invocation_names if name != entry["name"]
            )
            entries.append(entry)

        if filter_text:
            needle = filter_text.casefold()
            entries = [
                entry
                for entry in entries
                if needle in entry["name"].casefold()
                or any(needle in alias.casefold() for alias in entry["aliases"])
            ]
        return sorted(entries, key=lambda entry: entry["name"])

    def list_tasks_json(self, filter_text: str | None = None):
        """Output tasks as JSON for machine-readable consumption (e.g. qk-mcp)."""
        result = self._task_list_entries(filter_text)
        # Write directly to sys.stdout to bypass Rich and ensure clean JSON.
        sys.stdout.write(json.dumps(result))
        sys.stdout.write("\n")
        sys.stdout.flush()

    def list_tasks(self, filter_text: str | None = None):
        """List the available tasks."""
        import rich.box
        import rich.table
        import rich.text

        table = rich.table.Table(title="Available tasks", box=rich.box.ROUNDED)
        table.show_lines = True
        table.add_column("Task", style="bold yellow", no_wrap=True)
        table.add_column("Aliases", style="bold yellow", no_wrap=True)
        table.add_column("Short Description", style="bold yellow")
        table.add_column("Location")

        for entry in self._task_list_entries(filter_text):
            rich_task_name = rich.text.Text(entry["name"], style="bold")
            rich_aliases = rich.text.Text("\n".join(entry["aliases"]), style="dim")
            task_location = rich.text.Text(entry["location"] or "", style="dim")
            short_help = rich.text.Text(entry["short_help"], style="green")
            table.add_row(rich_task_name, rich_aliases, short_help, task_location)

        app.console.print(table)

    def get_usage(self) -> str:
        """Get the usage message."""
        return _parser.format_usage()

    def get_task(self, task_name: str) -> quickie.Task:
        """Get a task by name."""
        return app.tasks[task_name]

    def run_task(self, task_name: str, *, args):
        """Run a task."""
        task = self.get_task(task_name)
        return task.parse_and_run(args)

    def watch_task(
        self,
        task_name: str,
        *,
        args: list[str],
        watch_paths: list[str] | None,
        watch_exclude: list[str] | None,
        debounce: float | None = None,
        poll_interval: float | None = None,
    ):
        """Run a task in watch mode, re-running on file changes.

        :param task_name: The name of the task to run.
        :param args: Arguments to pass to the task.
        :param watch_paths: Glob patterns or directories to watch.
        :param watch_exclude: Glob patterns or directories to exclude.
        :param debounce: Seconds to wait after a change before re-running.
        :param poll_interval: Seconds between file-change polls.
        """
        from quickie._watcher import (
            FileWatcher,
            DEFAULT_DEBOUNCE,
            DEFAULT_POLL_INTERVAL,
        )
        from quickie.context import resolve_wd

        task = self.get_task(task_name)
        wd = resolve_wd(None)

        # Fall back to task-defined watch configuration when CLI args are
        # not explicitly provided.
        if debounce is None:
            debounce = task.watch_debounce
        if poll_interval is None:
            poll_interval = task.watch_interval
        if not watch_paths:
            watch_paths = list(task.watch_paths) or ["."]
        if not watch_exclude and task.watch_exclude:
            watch_exclude = list(task.watch_exclude)

        # Final fallback to module-level defaults
        if debounce is None:
            debounce = DEFAULT_DEBOUNCE
        if poll_interval is None:
            poll_interval = DEFAULT_POLL_INTERVAL

        watcher = FileWatcher(
            watch_paths=watch_paths,
            exclude=watch_exclude,
            wd=wd,
            debounce=debounce,
        )

        app.console.print(
            "[bold cyan]Watching for changes...[/bold cyan] (Ctrl+C to stop)"
        )
        app.console.print(f"  Task: [bold yellow]{task_name}[/bold yellow]")
        app.console.print(f"  Paths: [dim]{', '.join(watch_paths)}[/dim]")
        if watch_exclude:
            app.console.print(f"  Exclude: [dim]{', '.join(watch_exclude)}[/dim]")
        app.console.print()

        watcher.start()
        try:
            # Run the task immediately on first start
            app.console.print(f"[bold green]Running {task_name}...[/bold green]")
            task.parse_and_run(args)
            app.console.print()

            # Poll for changes
            while True:
                if watcher.has_changes():
                    msg = f"Changes detected, re-running {task_name}..."
                    app.console.print(f"[bold yellow]{msg}[/bold yellow]")
                    watcher.reset()
                    task.parse_and_run(args)
                    app.console.print()
                time.sleep(poll_interval)
        except KeyboardInterrupt:
            app.console.print("\n[bold red]Watching stopped.[/bold red]")
        finally:
            watcher.stop()
