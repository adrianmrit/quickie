"""Custom argument parser for quickie."""

import typing
from argparse import SUPPRESS, ArgumentParser

import argcomplete

from quickie._meta import __version__ as version
from quickie.completion._internal import TaskCompleter


class BaseArgumentParser(ArgumentParser):
    """Base argument parser with common arguments for qk and qk-mcp.

    Includes: verbosity, log-file, version, module path, and global flag.
    """

    @typing.override
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._add_common_arguments()

    def _add_common_arguments(self) -> None:
        """Add arguments common to both qk and qk-mcp."""
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


class AppArgumentParser(BaseArgumentParser):
    """Custom argument parser for quickie."""

    @typing.override
    def __init__(self):
        super().__init__(description="A CLI tool for quick tasks.")
        self._add_app_arguments()

    def _add_app_arguments(self) -> None:
        """Add arguments specific to the qk CLI."""
        self.add_argument(
            "-m", "--module", type=str, help="The module to load tasks from"
        )
        self.add_argument(
            "-g",
            "--global",
            action="store_true",
            dest="use_global",
            help="Use global tasks from ~/_qkg instead of project tasks",
        )
        self.add_argument("-l", "--list", action="store_true", help="List tasks")
        self.add_argument(
            "-lf",
            "--list-filter",
            nargs="?",
            const="",
            metavar="TEXT",
            help="Filter listed tasks by invocation name or alias",
        )
        self.add_argument(
            "--list-json",
            action="store_true",
            dest="list_json",
            help=SUPPRESS,
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
        self.add_argument(
            "-w",
            "--watch",
            action="store_true",
            dest="watch",
            help="Watch for file changes and re-run the task",
        )
        self.add_argument(
            "--watch-paths",
            action="append",
            dest="watch_paths",
            metavar="PATH",
            help="Directory paths to watch (repeatable). Defaults to the task "
            "working directory.",
        )
        self.add_argument(
            "--watch-ignore-paths",
            action="append",
            dest="watch_ignore_paths",
            metavar="PATH",
            help="Directory paths to ignore (repeatable).",
        )
        self.add_argument(
            "--watch-patterns",
            action="append",
            dest="watch_patterns",
            metavar="PATTERN",
            help="Patterns for changed files (repeatable; separate patterns with ';').",
        )
        self.add_argument(
            "--watch-ignore-patterns",
            action="append",
            dest="watch_ignore_patterns",
            metavar="PATTERN",
            help="Patterns to ignore (repeatable; separate patterns with ';').",
        )
        self.add_argument(
            "--watch-recursive",
            action="store_true",
            dest="watch_recursive",
            default=None,
            help="Watch directories recursively (default: false).",
        )
        self.add_argument(
            "--watch-debounce",
            type=float,
            dest="watch_debounce",
            metavar="SECS",
            default=None,
            help="Seconds to wait after a change before re-running (default: 0.5). "
            "Prevents rapid re-runs when multiple files change at once.",
        )
        self.add_argument("task", nargs="?", help="The task to run").completer = (  # type: ignore
            TaskCompleter()
        )
        # This does not need completion as it is handled by the task completer
        self.add_argument(
            "args", nargs="*", help="The arguments to pass to the task"
        ).completer = argcomplete.completers.SuppressCompleter()  # type: ignore

        self._value_flags: frozenset[str] = frozenset(
            opt
            for action in self._actions
            for opt in action.option_strings
            if action.nargs is None
        )

    @typing.override
    def parse_known_args(self, args=None, namespace=None):
        qk_args, task_args = self.partition_args(args)
        namespace, argv = super().parse_known_args(qk_args, namespace)

        if argv:
            # Because the unknown arguments are not task arguments, we raise an error
            msg = "unrecognized arguments: %s"
            self.error(msg % " ".join(argv))

        namespace.args = task_args
        return namespace, []

    def partition_args(self, args) -> tuple[list[str], list[str]]:
        """Split raw argv into (qk_args, task_args).

        qk_args contains all flags and values that belong to quickie itself,
        up to and including the task name. task_args contains everything after.
        """
        qk_args = []
        task_args = []
        args = iter(args)
        while (arg := next(args, None)) is not None:
            if arg in self._value_flags:
                qk_args.append(arg)
                qk_args.append(next(args))
            elif arg.startswith("-"):
                qk_args.append(arg)
            else:
                qk_args.append(arg)
                task_args = list(args)

        return qk_args, task_args


class MCPArgumentParser(BaseArgumentParser):
    """Argument parser for the qk-mcp MCP stdio server.

    Supports common arguments like verbosity and log file.
    """

    @typing.override
    def __init__(self):
        super().__init__(
            prog="qk-mcp",
            description="MCP stdio server that exposes quickie project tasks.",
        )
        self.add_argument(
            "--project",
            action="append",
            type=str,
            dest="projects",
            metavar="NAME:PATH",
            default=None,
            help=(
                "Register a project as NAME:PATH where PATH points to the _qk "
                "module or directory. Repeatable. Overrides --config on name conflict."
            ),
        )
        self.add_argument(
            "--config",
            type=str,
            dest="config",
            metavar="FILE",
            default=None,
            help=("Path to a TOML or JSON config file declaring projects to register."),
        )
