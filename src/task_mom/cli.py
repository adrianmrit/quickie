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
    Path("mtasks"),
    Path("_mtasks"),
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
        self.parser.add_argument("-V", "--version", action="version", version=version)
        self.parser.add_argument("task", nargs="?", help="The task to run")
        self.parser.add_argument(
            "args", nargs="*", help="The arguments to pass to the task"
        )

        self.load_tasks(task_paths)

    def __call__(self):
        """A CLI tool that does your chores while you slack off."""
        # Help message for the cli.
        # Optionally accepts a task name to show the help message for it
        main_args, task_name, task_args = self._partition_args(self.argv)
        _main_args = self.parser.parse_args(main_args)

        if task_name is not None:
            self.run_task(task_name=task_name, args=task_args)
        else:
            print(self.get_usage())
        self.parser.exit()

    def _partition_args(self, args):
        """Partition the arguments into main arguments and task arguments.

        We need this to avoid interpreting task arguments as main arguments. Also
        allows us to pass options to the task without using the `--` separator.
        """
        main_args = []
        task_name = None
        task_args = []
        current = main_args
        for arg in args:
            if not arg.startswith("-") and task_name is None:
                task_name = arg
                current = task_args
            else:
                current.append(arg)

        return main_args, task_name, task_args

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

    def run_task(self, task_name, args):
        """Run a task."""
        task = self.get_task(task_name)
        return task(args)
