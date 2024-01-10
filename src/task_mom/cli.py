"""The CLI entry of task-mom."""
import sys
import typing
from argparse import ArgumentParser
from pathlib import Path

from task_mom.context import GlobalContext

from ._version import __version__ as version
from .tasks import global_namespace
from .utils import imports

_DEFAULT_PATHS = (
    Path("mtasks.py"),
    Path("mtasks/__init__.py"),
    Path("_mtasks.py"),
    Path("_mtasks/__init__.py"),
)


def main(argv=None, *, task_paths=_DEFAULT_PATHS):
    """Run the CLI."""
    Main(argv=argv, task_paths=task_paths)()


class Main:
    """Represents the CLI entry of task-mom."""

    def __init__(  # noqa: PLR0913
        self, *, argv=None, task_paths, stdin=None, stdout=None, stderr=None
    ):
        """Initialize the CLI."""
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

        self.parser = ArgumentParser(add_help=False, description=main.__doc__)
        group = self.parser.add_mutually_exclusive_group()
        group.add_argument(
            "-h",
            "--help",
            nargs="?",
            const=True,
            metavar="TASK",
            help="show this help message, or the help message for a task, and exit",
        )
        group.add_argument("-V", "--version", action="version", version=version)
        task_group = self.parser.add_argument_group("Task")

        # Pass a task name, with optional arguments, to run it.
        # Cannot be used with -h or -V
        task_group.add_argument("task", nargs="?", metavar="TASK", help="task name")
        task_group.add_argument(
            "args", nargs="*", metavar="ARGS", help="task arguments"
        )
        self.load_tasks(task_paths)

    def __call__(self):
        """A CLI tool that does your chores while you slack off."""
        # Help message for the cli.
        # Optionally accepts a task name to show the help message for it
        args = self.parser.parse_args(self.argv)
        if args.help and args.task:
            print("error: -h/--help only accepts one task name")
            self.parser.exit(2)

        if args.help:
            if isinstance(args.help, str):
                help = self.get_task_help(args.help)
            else:
                help = self.get_help()
            print(help)
        elif args.task:
            self.run_task(args.task, args.args)
        else:
            print(self.get_usage())
        self.parser.exit()

    def load_tasks(self, paths: typing.Iterable[Path]):
        """Load tasks from the tasks module."""
        root = Path.cwd()
        for path in paths:
            try:
                # we discard the module. The tasks should be registered
                # in the global namespace
                imports.import_from_path(path, root=root)
            except imports.InternalImportError:
                pass

    def get_help(self):
        """Get the help message."""
        return self.parser.format_help()

    def get_usage(self):
        """Get the usage message."""
        return self.parser.format_usage()

    def get_task(self, task_name):
        """Get a task by name."""
        try:
            task_class = global_namespace.get_task_class(task_name)
            return task_class(name=task_name, context=GlobalContext.get())
        except KeyError:
            raise ValueError(f"Task {task_name!r} not found")

    def get_task_help(self, task_name):
        """Get the help message for a task."""
        task = self.get_task(task_name)
        return task.get_help()

    def run_task(self, task_name, args):
        """Run a task."""
        task = self.get_task(task_name)
        return task(args)
