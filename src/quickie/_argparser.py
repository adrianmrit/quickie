"""Custom argument parser for quickie."""

import sys
import typing
from argparse import SUPPRESS, ArgumentParser, RawDescriptionHelpFormatter

import argcomplete

from quickie._meta import __version__ as version
from quickie.commands import COMMANDS
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
        super().__init__(
            usage="qk [OPTIONS] COMMAND ... | qk [OPTIONS] TASK [ARGS ...]",
            description="A CLI tool for quick tasks.",
            epilog=(
                "Examples:\n"
                "  qk build\n"
                "  qk test unit --fast\n"
                "  qk :list\n"
                "  qk :watch --paths src build"
            ),
            formatter_class=RawDescriptionHelpFormatter,
        )
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
        self.set_defaults(task=None, args=[])
        commands = self.add_subparsers(
            dest="command",
            title="commands",
            description="Built in commands.",
            metavar="COMMAND",
            parser_class=ArgumentParser,
        )
        self.commands_action = commands
        self.command_parsers: dict[str, ArgumentParser] = {}
        # Register each command, letting it configure its own parser
        public_command_names: list[str] = []
        for name, command in COMMANDS.items():
            if name == ":run":
                # :run is hidden from help; kept as the default runner for
                # bare task names via _normalize_args.
                run = commands.add_parser(":run", help=SUPPRESS, add_help=False)
                commands._choices_actions.pop()
                self.run_parser = run
                self.command_parsers[":run"] = run
            else:
                parser = commands.add_parser(
                    name,
                    help=command.__doc__,
                    usage=f"qk {name} [OPTIONS]",
                    description=command.__doc__,
                )
                public_command_names.append(name)
                self.command_parsers[name] = parser
            command.configure_parser(run if name == ":run" else parser)  # type: ignore[possibly-undefined]
        commands.completer = argcomplete.completers.ChoicesCompleter(  # type: ignore
            public_command_names  # type: ignore[arg-type]
        )
        self.add_argument(
            "task_name",
            nargs="?",
            metavar="TASK",
            help="Name of the task to run",
        ).completer = TaskCompleter()  # type: ignore
        self.add_argument(
            "task_args",
            nargs="*",
            metavar="ARGS",
            help="Arguments passed to the task",
        )
        self.task_completion_parser = BaseArgumentParser(
            prog=self.prog,
            description=self.description,
            add_help=False,
        )
        self.task_completion_parser.add_argument(
            "-m", "--module", type=str, help=SUPPRESS
        )
        self.task_completion_parser.add_argument(
            "-g", "--global", action="store_true", dest="use_global", help=SUPPRESS
        )
        self.task_completion_parser.add_argument(
            "-h", "--help", action="help", help="Show this help message and exit"
        )
        self.task_completion_parser.add_argument(
            "task",
            nargs="?",
            help=SUPPRESS,
        ).completer = TaskCompleter(  # type: ignore
            {
                name: command.__doc__ or ""
                for name, command in COMMANDS.items()
                if name != ":run"
            }
        )

    def _command_index(self, args: list[str]) -> int | None:
        """Locate the command or task after global options."""
        value_flags = {"-m", "--module", "--log-file"}
        iterator = iter(enumerate(args))
        for index, arg in iterator:
            if arg in value_flags:
                next(iterator, None)
            elif not arg.startswith("-"):
                return index
        return None

    def _normalize_args(self, args: list[str]) -> list[str]:
        """Route ordinary task invocations through the hidden run subcommand."""
        index = self._command_index(args)
        if index is not None and not args[index].startswith(":"):
            return args[:index] + [":run"] + args[index:]
        return args

    @typing.override
    def parse_args(self, args=None, namespace=None):
        if args is None:
            args = sys.argv[1:]
        parsed, unknown = self.parse_known_args(args, namespace)
        if unknown:
            self.error(f"unrecognized arguments: {' '.join(unknown)}")
        return parsed

    @typing.override
    def parse_known_args(self, args=None, namespace=None):
        if args is None:
            args = sys.argv[1:]
        normalized = self._normalize_args(list(args))
        parsed, unknown = super().parse_known_args(normalized, namespace)
        if parsed.command in (":run", ":watch") and parsed.task:
            tail_index = len(normalized) - len(parsed.args)
            # argparse consumes a separator immediately following the task.
            if normalized[tail_index - 1] == "--":
                parsed.args.insert(0, "--")
        return parsed, unknown


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
