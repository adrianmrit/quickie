"""Custom argument parser for task-mom."""

import typing
from argparse import ArgumentParser

import argcomplete

from ._version import __version__ as version
from .namespace import global_namespace

if typing.TYPE_CHECKING:
    from .cli import Main
else:
    Main = typing.Any


class _TaskCompleter:
    def __init__(self, main: Main):
        self.main = main

    def __call__(self, prefix, action, parser, parsed_args):
        try:
            self.main.load_tasks_from_namespace(parsed_args)
            return [key for key in global_namespace.keys() if key.startswith(prefix)]
        except Exception as e:
            argcomplete.warn("Autocompletion failed with error:", e)


class MomArgumentsParser(ArgumentParser):
    """Custom argument parser for task-mom."""

    @typing.override
    def __init__(self, main):
        super().__init__(description="A CLI tool that does your chores")
        module_or_global_group = self.add_mutually_exclusive_group()
        self.add_argument("-V", "--version", action="version", version=version)
        self.add_argument("-l", "--list", action="store_true", help="List tasks")
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
        module_or_global_group.add_argument(
            "--autocomplete",
            help="Suggest autocompletion for the shell",
            dest="suggest_auto_completion",
            choices=["bash", "zsh"],
        )
        self.add_argument(
            "task", nargs="?", help="The task to run"
        ).completer = _TaskCompleter(main)
        self.add_argument("args", nargs="*", help="The arguments to pass to the task")

    @typing.override
    def parse_known_args(self, args=None, namespace=None):
        mom_args, task_args = self._partition_args(args)
        namespace, argv = super().parse_known_args(mom_args, namespace)

        if argv:
            # Because the unknown arguments are not task arguments, we raise an error
            msg = "unrecognized arguments: %s"
            self.error(msg % " ".join(argv))

        # namespace.task = task
        namespace.args = task_args
        return namespace, []

    def _partition_args(self, args):
        mom_args = []
        task_args = []
        args = iter(args)
        while arg := next(args, None):
            if arg in {"-m", "--module", "--autocomplete"}:
                mom_args.append(arg)
                mom_args.append(next(args))
            elif arg.startswith("-"):
                mom_args.append(arg)
            else:
                # Task found
                mom_args.append(arg)
                # The rest of the arguments are task arguments
                task_args = list(args)

        return mom_args, task_args
