"""The CLI entry of quickie."""

import os
import sys
from contextlib import redirect_stderr
from functools import cached_property, wraps
from io import StringIO

import argcomplete

import quickie
from quickie import app
from quickie._argparser import AppArgumentParser
from quickie._launcher import Launcher
from quickie.commands import COMMANDS as COMMANDS_DICT
from quickie.errors import QuickieError, Skip, Stop

_parser = AppArgumentParser()


def _autocomplete(parser):
    """Run argcomplete while hiding the internal runner command."""
    choices = _parser.commands_action.choices
    hidden_runner = choices.pop(":run", None)
    try:
        argcomplete.autocomplete(parser)
    finally:
        if hidden_runner is not None:
            choices[":run"] = hidden_runner


def _clean_exit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            print("Exiting due to KeyboardInterrupt.")
            sys.exit(1)

    return wrapper


def _launch(argv, *, global_, use_global):
    """Delegate to the project executable when appropriate."""
    launcher = Launcher()
    if not global_ and not use_global and not launcher.is_in_recursion():
        try:
            app.logger.debug("Attempting launcher discovery...")
            exit_code = launcher.launch(argv)
            sys.exit(exit_code)
        except QuickieError as e:
            app.logger.debug(f"Launcher discovery failed: {e}")
        except Exception as e:
            app.logger.debug(f"Unexpected error in launcher: {e}")


@_clean_exit
def main(argv=None, *, raise_error=False, global_=False):  # noqa: PLR0912
    """Run the CLI."""
    from rich import traceback

    traceback.install(suppress=[quickie])

    if argv is None:
        argv = sys.argv[1:]

    main_obj = Main(argv=argv, global_=global_)
    if os.environ.get("_ARGCOMPLETE"):
        main_obj.handle_autocomplete()
        return  # handle_autocomplete calls sys.exit

    app.set_verbosity(main_obj.namespace.verbosity)
    _launch(argv, global_=global_, use_global=main_obj.namespace.use_global)

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

    @cached_property
    def namespace(self):
        """Parse complete invocation arguments only when execution needs them."""
        return _parser.parse_args(self.argv)

    def handle_autocomplete(self):
        """Handle argcomplete tab completion. Calls sys.exit."""
        arg_complete_val = os.environ["_ARGCOMPLETE"]
        comp_line = os.environ["COMP_LINE"]
        comp_point = int(os.environ["COMP_POINT"])

        start = int(arg_complete_val)
        split_line = argcomplete.lexers.split_line(comp_line, comp_point)
        split_words = split_line[3]
        prefix = split_line[1]
        raw_args = split_words[start:]
        normalized_args = _parser._normalize_args(list(raw_args))
        command_index = _parser._command_index(normalized_args)
        command_name = (
            normalized_args[command_index] if command_index is not None else None
        )
        if (command_index is None and prefix.startswith(":")) or (
            command_name is not None
            and command_name.startswith(":")
            and command_name not in COMMANDS_DICT
        ):
            _autocomplete(_parser)
            sys.exit(0)
        with redirect_stderr(StringIO()):
            try:
                namespace = _parser.task_completion_parser.parse_args(
                    normalized_args[:command_index]
                    if command_index is not None
                    else normalized_args
                )
            except SystemExit:
                _autocomplete(_parser.task_completion_parser)
                sys.exit(0)

        app.set_verbosity(namespace.verbosity)
        use_global = self.global_ or namespace.use_global
        _launch(self.argv, global_=self.global_, use_global=use_global)
        app.set_log_file(namespace.log_file)
        if not use_global and namespace.module:
            app.set_project_path(namespace.module)
        app.set_use_global(use_global)

        # --- Fast path: try the disk cache ---
        app._try_load_task_cache()
        cache_available = app.cached_task_names is not None

        command = COMMANDS_DICT.get(command_name) if command_name is not None else None
        if command is None:
            # Task-name completion — cache is sufficient
            if not cache_available:
                try:
                    app.load_tasks()
                except QuickieError:
                    pass
            _autocomplete(_parser.task_completion_parser)
            sys.exit(0)
        assert command_index is not None and command_name is not None
        # Normalization inserts :run for bare tasks, but not into the shell line.
        inserted_runner = normalized_args != list(raw_args)
        os.environ["_ARGCOMPLETE"] = str(
            start + command_index + (0 if inserted_runner else 1)
        )
        command.autocomplete(
            _parser.command_parsers[command_name],
            normalized_args[command_index + 1 :],
        )
        sys.exit(0)

    def __call__(self):
        """Run the CLI."""
        namespace = self.namespace

        app.set_log_file(namespace.log_file)
        use_global = self.global_ or namespace.use_global
        if not use_global and namespace.module:
            app.set_project_path(namespace.module)
        app.set_use_global(use_global)

        command = COMMANDS_DICT.get(namespace.command)
        if command is not None:
            app.logger.info(f"Running quickie {quickie.__version__}")
            if namespace.command in (":list", ":watch", ":run", ":autocomplete"):
                app.load_tasks()
            command.execute(namespace)
        else:
            from rich.text import Text

            app.console.print(Text.from_ansi(self.get_usage()))
        _parser.exit()

    def get_usage(self) -> str:
        """Get the usage message."""
        return _parser.format_usage()

    def get_task(self, task_name: str) -> quickie.Task:
        """Get a task by name."""
        return app.tasks[task_name]
