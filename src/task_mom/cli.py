"""The CLI entry of task-mom."""
import sys
from argparse import ArgumentParser

from task_mom.context import GlobalContext

from ._version import __version__ as version
from .tasks import global_namespace

_DEFAULT_PATHS = (
    "mtasks.py",
    "mtasks/__init__.py",
    "_mtasks.py",
    "_mtasks/__init__.py",
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

    def load_tasks(self, paths):
        """Load tasks from the tasks module."""
        import os
        from importlib.util import module_from_spec, spec_from_file_location

        cwd = os.getcwd()

        for path in paths:
            full_path = os.path.join(cwd, path)
            # check path exists
            if os.path.exists(full_path):
                break
        else:
            paths_str = ", ".join(paths)
            raise FileNotFoundError(f"Could not find any of {paths_str}")

        spec = spec_from_file_location("_mtasks", full_path)
        if spec is not None:
            module = module_from_spec(spec)
            sys.modules["_mtasks"] = module
            spec.loader.exec_module(module)  # type: ignore

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
