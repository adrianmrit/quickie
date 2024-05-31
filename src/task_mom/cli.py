"""The CLI entry of task-mom."""

import os
import sys
import tomllib
import typing
from argparse import ArgumentParser
from pathlib import Path

from frozendict import frozendict
from rich import traceback
from rich.console import Console
from rich.theme import Theme

import task_mom
from task_mom.context import Context

from . import settings
from ._version import __version__ as version
from .loader import load_tasks_from_module
from .namespace import global_namespace
from .utils import imports

_DEFAULT_PATH = Path("mom_tasks")
_HOME_PATH = Path.home() / "mom"
_SETTINGS_PATH = _HOME_PATH / "settings.toml"


class MomError(Exception):
    """Base class for task-mom errors."""

    def __init__(self, message, *, exit_code):
        """Initialize the error."""
        super().__init__(message)
        self.exit_code = exit_code


class TaskNotFoundError(MomError):
    """Raised when a task is not found."""

    def __init__(self, task_name):
        """Initialize the error."""
        super().__init__(f"Task '{task_name}' not found", exit_code=1)


class TasksModuleNotFoundError(MomError):
    """Raised when a module is not found."""

    def __init__(self, module_name):
        """Initialize the error."""
        super().__init__(f"Tasks module {module_name} not found", exit_code=2)


def main(argv=None, *, raise_error=False):
    """Run the CLI."""

    traceback.install(suppress=[task_mom])
    main = Main(argv=argv)
    try:
        main()
    except MomError as e:
        if raise_error:
            raise e
        main.console.print(f"Error: [error]{e}[/error]", style="error")
        sys.exit(e.exit_code)


class Main:
    """Represents the CLI entry of task-mom."""

    def __init__(self, *, argv=None):  # noqa: PLR0913
        """Initialize the CLI."""
        self.settings = self.load_settings()
        if argv is None:
            argv = sys.argv[1:]
        self.argv = argv

        self.console = Console(theme=Theme(self.settings["style"]))

        self.global_context = Context(
            program_name=os.path.basename(sys.argv[0]),
            cwd=os.getcwd(),
            env=frozendict(os.environ),
            console=self.console,
        )

        self.parser = ArgumentParser(description="A CLI tool that does your chores")
        module_or_global_group = self.parser.add_mutually_exclusive_group()
        self.parser.add_argument("-V", "--version", action="version", version=version)
        self.parser.add_argument("-l", "--list", action="store_true", help="List tasks")
        module_or_global_group.add_argument(
            "-m", "--module", type=str, help="The module to load tasks from"
        )
        module_or_global_group.add_argument(
            "-g",
            "--global",
            action="store_true",
            help="Use global defined tasks",
            dest="use_global",
        )
        self.parser.add_argument("task", nargs="?", help="The task to run")
        self.parser.add_argument(
            "args", nargs="*", help="The arguments to pass to the task"
        )

    def __call__(self):
        """A CLI tool that does your chores while you slack off."""
        # Help message for the cli.
        # Optionally accepts a task name to show the help message for it
        main_args, task_name, task_args = self._partition_args(self.argv)
        main_args = self.parser.parse_args(main_args)

        if main_args.module is not None:
            tasks_module_path = Path(main_args.module)
        elif main_args.use_global:
            tasks_module_path = _HOME_PATH
        else:
            tasks_module_path = self.get_default_module_path()

        modules = self.load_tasks(path=tasks_module_path)

        if main_args.list:
            self.list_tasks(modules)
        elif task_name is not None:
            self.run_task(task_name=task_name, args=task_args)
        else:
            self.console.print(self.get_usage())
        self.parser.exit()

    def load_settings(self):
        """Load the console theme."""
        defaults = frozendict({"style": settings.DEFAULT_CONSOLE_STYLE})
        if _SETTINGS_PATH.exists():
            with _SETTINGS_PATH.open("r") as f:
                user_settings = tomllib.load(f)
                user_settings["style"] = frozendict(
                    defaults["style"] | user_settings.get("style", {})
                )
                return frozendict(user_settings)
        return defaults

    def list_tasks(self, modules):
        """List the available tasks."""
        self.console.print("Available tasks:\n", style="bold green")
        # TODO: Improve this
        for task_name in global_namespace._internal_namespace.keys():
            self.console.print(f"  {task_name}", style="info")
        self.console.print()

    def _partition_args(self, args):
        """Partition the arguments into main arguments and task arguments.

        We need this to avoid interpreting task arguments as main arguments. Also
        allows us to pass options to the task without using the `--` separator.
        """
        main_args = []
        task_name = None
        task_args = []
        current = main_args
        args = iter(args)
        while arg := next(args, None):
            # Everything after the task name is a task argument
            if task_name is None:
                # Check if we are passing a module before the task name
                if arg == "-m" or arg.startswith("--module"):
                    next_arg = next(args, None)
                    # If value not provided, it should be caught by the parser
                    if next_arg is not None:
                        current.append(arg)
                        current.append(next_arg)
                        continue
                # Check if we found the task name
                elif not arg.startswith("-"):
                    task_name = arg
                    current = task_args
                    continue
            current.append(arg)

        return main_args, task_name, task_args

    def get_default_module_path(self):
        """Get the default module path."""
        current = Path.cwd()
        while True:
            path = current / _DEFAULT_PATH
            if (path).exists():
                return path
            if current == current.parent:
                break
            current = current.parent
        raise TasksModuleNotFoundError(_DEFAULT_PATH)

    def load_tasks(self, *, path: Path):
        """Load tasks from the tasks module."""
        root = Path.cwd()
        module = imports.import_from_path(root / path)
        load_tasks_from_module(module)

    def get_usage(self):
        """Get the usage message."""
        return self.parser.format_usage()

    def get_task(self, task_name):
        """Get a task by name."""
        try:
            task_class = global_namespace.get_task_class(task_name)
            return task_class(name=task_name, context=self.global_context)
        except KeyError:
            raise TaskNotFoundError(task_name)

    def run_task(self, task_name, args):
        """Run a task."""
        task = self.get_task(task_name)
        return task(args)
