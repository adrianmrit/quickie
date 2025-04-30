"""Custom argument parser for quickie."""

import typing
from argparse import ArgumentParser

import argcomplete

from quickie._meta import __version__ as version
from quickie.completion._internal import TaskCompleter


class AppArgumentParser(ArgumentParser):
    """Custom argument parser for quickie."""

    @typing.override
    def __init__(self, main):
        super().__init__(description="A CLI tool for quick tasks.")
        # argument for logging level
        self.add_argument(
            "-v",
            "--verbose",
            action="count",
            dest="verbosity",
            default=0,
            help="Increase verbosity (repeat for increased verbosity)",
        )
        self.add_argument(
            "-q",
            "--quiet",
            action="store_const",
            const=-1,
            default=0,
            dest="verbosity",
            help="Decrease verbosity (show errors only)",
        )
        self.add_argument(
            "--log-file",
            type=str,
            help="The file to log to. If not set, logs to stdout.",
        )
        self.add_argument("-V", "--version", action="version", version=version)
        self.add_argument("-l", "--list", action="store_true", help="List tasks")
        self.add_argument(
            "-m", "--module", type=str, help="The module to load tasks from"
        )
        self.add_argument(
            "--init",
            nargs="?",
            help="Initialize a quickie project in the directory",
            const=".",
            metavar="DIR",
        ).completer = argcomplete.completers.FilesCompleter()  # type: ignore
        self.add_argument(
            "--autocomplete",
            help="Suggest autocompletion for the shell",
            dest="suggest_auto_completion",
            choices=["bash", "zsh"],
        ).completer = argcomplete.completers.ChoicesCompleter(  # type: ignore
            ["bash", "zsh"]
        )
        self.add_argument("task", nargs="?", help="The task to run").completer = (  # type: ignore
            TaskCompleter()
        )
        # This does not need completion as it is handled by the task completer
        self.add_argument(
            "args", nargs="*", help="The arguments to pass to the task"
        ).completer = argcomplete.completers.SuppressCompleter()  # type: ignore

    @typing.override
    def parse_known_args(self, args=None, namespace=None):
        qk_args, task_args = self._partition_args(args)
        namespace, argv = super().parse_known_args(qk_args, namespace)

        if argv:
            # Because the unknown arguments are not task arguments, we raise an error
            msg = "unrecognized arguments: %s"
            self.error(msg % " ".join(argv))

        # namespace.task = task
        namespace.args = task_args
        return namespace, []

    def _partition_args(self, args):
        qk_args = []
        task_args = []
        args = iter(args)
        while arg := next(args, None):
            if arg in {"-m", "--module", "--autocomplete"}:
                qk_args.append(arg)
                qk_args.append(next(args))
            elif arg.startswith("-"):
                qk_args.append(arg)
            else:
                # Task found
                qk_args.append(arg)
                # The rest of the arguments are task arguments
                task_args = list(args)

        return qk_args, task_args
