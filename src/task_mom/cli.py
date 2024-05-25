"""The CLI entry of task-mom."""

import sys
import typing
from argparse import ArgumentParser
from pathlib import Path

from task_mom.context import GlobalContext

from ._version import __version__ as version
from .loader import load_tasks_from_module
from .namespace import global_namespace
from .utils import imports

_DEFAULT_PATHS = (Path("mom_tasks"),)


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
        super().__init__(f"Task {task_name!r} not found", exit_code=1)


class ModuleNotFoundError(MomError):
    """Raised when a module is not found."""

    def __init__(self, module_name):
        """Initialize the error."""
        super().__init__(f"Module {module_name!r} not found", exit_code=2)


def main(argv=None, *, task_paths=_DEFAULT_PATHS, raise_error=False):
    """Run the CLI."""

    try:
        Main(argv=argv, task_paths=task_paths)()
    except MomError as e:
        if raise_error:
            raise e
        print(f"Error: {e}")
        sys.exit(e.exit_code)


class Main:
    """Represents the CLI entry of task-mom."""

    def __init__(  # noqa: PLR0913
        self, *, argv=None, task_paths, stdin=None, stdout=None, stderr=None
    ):
        """Initialize the CLI."""
        if argv is None:
            argv = sys.argv[1:]
        self.argv = argv

        if stdin is None:
            stdin = sys.stdin
        if stdout is None:
            stdout = sys.stdout
        if stderr is None:
            stderr = sys.stderr

        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr

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
            required = True
            paths = [Path(main_args.module)]
        elif main_args.use_global:
            required = True
            paths = [self.get_global_module_path()]
        else:
            required = False
            paths = _DEFAULT_PATHS

        modules = self.load_tasks(paths=paths, required=required)

        if main_args.list:
            self.list_tasks(modules)
        elif task_name is not None:
            self.run_task(task_name=task_name, args=task_args)
        else:
            print(self.get_usage())
        self.parser.exit()

    def list_tasks(self, modules):
        """List the available tasks."""
        print("Available tasks:\n")
        # TODO: Improve this
        for task_name in global_namespace._internal_namespace.keys():
            print(f"  {task_name}")
        print()

    def get_global_module_path(self):
        """Get the global tasks."""
        return Path.home() / "mom_tasks"

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

    def load_tasks(self, *, paths: typing.Iterable[Path], required: bool):
        """Load tasks from the tasks module."""
        root = Path.cwd()
        for path in paths:
            try:
                # we discard the module. The tasks should be registered
                # in the global namespace
                module = imports.import_from_path(root / path)
                load_tasks_from_module(module)
            except imports.InternalImportError as e:
                if required:
                    raise ModuleNotFoundError(path) from e

    def get_usage(self):
        """Get the usage message."""
        return self.parser.format_usage()

    def get_task(self, task_name):
        """Get a task by name."""
        try:
            task_class = global_namespace.get_task_class(task_name)
            return task_class(name=task_name, context=GlobalContext.get())
        except KeyError:
            raise TaskNotFoundError(f"Task {task_name!r} not found")

    def run_task(self, task_name, args):
        """Run a task."""
        task = self.get_task(task_name)
        try:
            return task(args)
        except Exception as e:
            raise RuntimeError(f"Error running task {task_name!r}") from e
