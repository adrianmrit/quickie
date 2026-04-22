"""The CLI entry of quickie."""

import json
import os
import sys
from functools import wraps

import argcomplete
import rich.box
import rich.table
import rich.text
from rich import traceback

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

        try:
            app.load_tasks()
        except QuickieError:
            pass  # Outside a project; TaskCompleter returns empty gracefully

        if namespace.task:
            try:
                task = self.get_task(namespace.task)
            except (QuickieError, KeyError):
                parser = _parser
            else:
                # Update _ARGCOMPLETE to the index of the task, so that
                # completion only considers the task arguments
                os.environ["_ARGCOMPLETE"] = str(args.index(namespace.task))
                parser = task.parser

        else:
            parser = _parser
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
            self.list_tasks_json()
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
            self.list_tasks()
        elif namespace.task is not None:
            app.load_tasks()
            self.run_task(
                task_name=namespace.task,
                args=namespace.args,
            )
        else:
            app.console.print(self.get_usage())
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

    def list_tasks_json(self):
        """Output tasks as JSON for machine-readable consumption (e.g. qk-mcp)."""
        cwd = os.getcwd()
        seen: dict[int, dict] = {}
        for invocation_name, task in app.tasks.items():
            task_id = id(task)
            if task_id not in seen:
                seen[task_id] = task.to_info_dict(cwd)
            entry = seen[task_id]
            if invocation_name not in entry["aliases"]:
                entry["aliases"].append(invocation_name)
        result = sorted(seen.values(), key=lambda t: t["name"])
        # Write directly to sys.stdout to bypass Rich and ensure clean JSON.
        sys.stdout.write(json.dumps(result))
        sys.stdout.write("\n")
        sys.stdout.flush()

    def list_tasks(self):
        """List the available tasks."""
        table = rich.table.Table(title="Available tasks", box=rich.box.SIMPLE)
        table.add_column("Task", style="bold yellow")
        table.add_column("Aliases", style="bold yellow")
        table.add_column("Short Description", style="bold yellow")
        table.add_column("Location", style="bold yellow")

        # Invert the task dictionary to group by class
        cwd = os.getcwd()
        names_by_task: dict[quickie.Task, list[str]] = {}
        for invocation_name, task in sorted(
            app.tasks.items(),
            key=lambda x: (
                x[1]._get_relative_file_location(cwd) or "",
                x[0].count(":"),
                x[0].split(":"),
            ),
        ):
            names_by_task.setdefault(task, []).append(invocation_name)

        for task, task_names in names_by_task.items():
            aliases = ", ".join(
                sorted(name for name in task_names if name != task.name)
            )
            rich_task_name = rich.text.Text(task.name, style="bold")
            rich_aliases = rich.text.Text(aliases, style="dim")
            task_location = rich.text.Text(
                task._get_relative_file_location(cwd) or "", style="dim"
            )
            short_help = rich.text.Text(task.get_short_help(), style="green")
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
