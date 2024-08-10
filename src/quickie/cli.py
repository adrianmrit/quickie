"""The CLI entry of quickie."""

import os
import sys
import tomllib
from functools import cached_property
from pathlib import Path

import argcomplete
from frozendict import frozendict
from rich import traceback
from rich.console import Console
from rich.theme import Theme

import quickie
from quickie import constants
from quickie.argparser import ArgumentsParser
from quickie.context import Context
from quickie.errors import QuickieError, TaskNotFoundError
from quickie.loader import get_default_module_path, load_tasks_from_module
from quickie.namespace import RootNamespace
from quickie.utils import imports


def main(argv=None, *, raise_error=False):
    """Run the CLI."""
    traceback.install(suppress=[quickie])
    main = Main(argv=argv)
    try:
        main()
    except QuickieError as e:
        if raise_error:
            raise e
        main.console.print(f"Error: [error]{e}[/error]", style="error")
        sys.exit(e.exit_code)


class Main:
    """Represents the CLI entry of quickie."""

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

        self.parser = ArgumentsParser(main=self)

    def __call__(self):
        """Run the CLI."""
        if os.environ.get("_ARGCOMPLETE"):
            comp_line = os.environ["COMP_LINE"]
            comp_point = int(os.environ["COMP_POINT"])

            # Hack to parse the arguments
            (_, _, _, comp_words, _) = argcomplete.lexers.split_line(
                comp_line, comp_point
            )

            # _ARGCOMPLETE is set by the shell script to tell us where comp_words
            # should start, based on what we're completing.
            # we ignore teh program name, hence no -1
            start = int(os.environ["_ARGCOMPLETE"])
            comp_words = comp_words[start:]
            namespace = self.parser.parse_args(comp_words)
            if namespace.task:
                self.load_tasks_from_namespace(namespace)
                task = self.get_task(namespace.task)
                os.environ["_ARGCOMPLETE"] = str(comp_words.index(namespace.task))
                argcomplete.autocomplete(task.parser)
            else:
                argcomplete.autocomplete(self.parser)

        namespace = self.parser.parse_args(self.argv)
        self.load_tasks_from_namespace(namespace)
        if namespace.suggest_auto_completion:
            if namespace.suggest_auto_completion == "bash":
                self.suggest_autocompletion_bash()
            elif namespace.suggest_auto_completion == "zsh":
                self.suggest_autocompletion_zsh()
        elif namespace.list:
            self.list_tasks()
        elif namespace.task is not None:
            self.run_task(task_name=namespace.task, args=namespace.args)
        else:
            self.console.print(self.get_usage())
        self.parser.exit()

    @cached_property
    def tasks_namespace(self):
        """Get the namespace."""
        return RootNamespace()

    def suggest_autocompletion_bash(self):
        """Suggest autocompletion for bash."""
        self.console.print("Add the following to ~/.bashrc or ~/.bash_profile:")
        self.console.print(
            'eval "$(register-python-argcomplete qck)"',
            style="bold green",
        )

    def suggest_autocompletion_zsh(self):
        """Suggest autocompletion for zsh."""
        self.console.print("Add the following to ~/.zshrc:")
        self.console.print(
            'eval "$(register-python-argcomplete qck)"',
            style="bold green",
        )

    def load_tasks_from_namespace(self, namespace):
        """Load tasks from the namespace."""
        if namespace.module is not None:
            tasks_module_path = Path(namespace.module)
        elif namespace.use_global:
            tasks_module_path = constants.HOME_PATH
        else:
            tasks_module_path = get_default_module_path()
        self.load_tasks(path=tasks_module_path)

    def load_settings(self):
        """Load the console theme."""
        defaults = frozendict({"style": constants.DEFAULT_CONSOLE_STYLE})
        if constants.SETTINGS_PATH.exists():
            with constants.SETTINGS_PATH.open("r") as f:
                user_settings = tomllib.load(f)
                user_settings["style"] = frozendict(
                    defaults["style"] | user_settings.get("style", {})
                )
                return frozendict(user_settings)
        return defaults

    def list_tasks(self):
        """List the available tasks."""
        import rich.text
        import rich.tree

        tree = rich.tree.Tree(
            "Available tasks:", style="bold green", guide_style="info"
        )
        node_by_namespace = {}
        for task_path, task in sorted(self.tasks_namespace.items(), key=lambda x: x[0]):
            if ":" in task_path:
                namespace, task_name = task_path.rsplit(":", 1)
            else:
                task_name = task_path
                namespace = ""

            task_info = rich.text.Text(task_name, style="info")
            if task._meta.short_help:
                task_info.append(f"\n  {task._meta.short_help}", style="green")
            if namespace:
                if namespace not in node_by_namespace:
                    node_by_namespace[namespace] = tree.add(
                        namespace, style="bold yellow", guide_style="yellow"
                    )
                node = node_by_namespace[namespace]
            else:
                node = tree
            node.add(task_info)
        self.console.print(tree)

    def load_tasks(self, *, path: Path):
        """Load tasks from the tasks module."""
        root = Path.cwd()
        module = imports.import_from_path(root / path)
        load_tasks_from_module(module, namespace=self.tasks_namespace)

    def get_usage(self):
        """Get the usage message."""
        return self.parser.format_usage()

    def get_task(self, task_name):
        """Get a task by name."""
        try:
            task_class = self.tasks_namespace.get_task_class(task_name)
            return task_class(name=task_name, context=self.global_context)
        except KeyError:
            raise TaskNotFoundError(task_name)

    def run_task(self, task_name, args):
        """Run a task."""
        task = self.get_task(task_name)
        return task(args)
