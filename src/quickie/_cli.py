"""The CLI entry of quickie."""

import os
import sys
from pathlib import Path

import argcomplete
from frozendict import frozendict
from rich import traceback
from rich.console import Console
from rich.theme import Theme

import quickie
from quickie import config
from quickie._argparser import ArgumentsParser
from quickie._loader import load_tasks_from_module
from quickie._namespace import RootNamespace
from quickie.context import Context
from quickie.errors import QuickieError, Stop
from quickie.utils import imports


def main(argv=None, *, raise_error=False, tasks_namespace=None, global_=False):
    """Run the CLI."""
    traceback.install(suppress=[quickie])
    main = Main(argv=argv, root_namespace=tasks_namespace, global_=global_)
    try:
        main()
    except Stop as e:
        if e.message:
            main.console.print(f"Stopping: [info]{e.message}[/info]", style="info")
        else:
            main.console.print(
                f"Stopping because {Stop.__name__} exception was raised."
            )
        sys.exit(e.exit_code)
    except QuickieError as e:
        if raise_error:
            raise e
        main.console.print(f"Error: [error]{e}[/error]", style="error")
        sys.exit(e.exit_code)


def global_main(argv=None, *, raise_error=False, tasks_namespace=None):
    """Run the CLI with the global option."""
    main(
        argv=argv,
        raise_error=raise_error,
        tasks_namespace=tasks_namespace,
        global_=True,
    )


class Main:
    """Represents the CLI entry of quickie."""

    def __init__(
        self, *, argv=None, root_namespace: RootNamespace | None = None, global_=False
    ):  # noqa: PLR0913
        """Initialize the CLI."""
        if argv is None:
            argv = sys.argv[1:]
        self.argv = argv

        # TODO: Make the console theme configurable
        self.console = Console(theme=Theme(config.CONSOLE_STYLE))
        if root_namespace is None:
            root_namespace = RootNamespace()
        self.root_namespace = root_namespace
        self.parser = ArgumentsParser(main=self)
        self.global_ = global_

    def __call__(self):
        """Run the CLI."""
        arg_complete_val = os.environ.get("_ARGCOMPLETE")
        if arg_complete_val:
            comp_line = os.environ["COMP_LINE"]
            comp_point = int(os.environ["COMP_POINT"])

            # Hack to parse the arguments
            (_, _, _, comp_words, _) = argcomplete.lexers.split_line(
                comp_line, comp_point
            )

            # _ARGCOMPLETE is set by the shell script to tell us where comp_words
            # should start, based on what we're completing.
            # we ignore teh program name, hence no -1
            start = int(arg_complete_val)
            args = comp_words[start:]
        else:
            args = self.argv

        namespace = self.parser.parse_args(args)
        config = self.get_config(
            tasks_module_name=namespace.module,
            use_global=self.global_,
        )
        context = Context(
            program_name=os.path.basename(sys.argv[0]),
            cwd=os.getcwd(),
            env=frozendict(os.environ),
            console=self.console,
            namespace=self.root_namespace,
            config=config,
        )
        self.load_tasks(path=config.TASKS_MODULE_PATH)

        if arg_complete_val:
            if namespace.task:
                task = self.get_task(namespace.task, context=context)
                # Upddate _ARGCOMPLETE to the index of the task, so that completion
                # only considers the task arguments
                os.environ["_ARGCOMPLETE"] = str(args.index(namespace.task))
                argcomplete.autocomplete(task.parser)
            else:
                argcomplete.autocomplete(self.parser)
            sys.exit(0)

        if namespace.suggest_auto_completion:
            if namespace.suggest_auto_completion == "bash":
                self.suggest_autocompletion_bash()
            elif namespace.suggest_auto_completion == "zsh":
                self.suggest_autocompletion_zsh()
        elif namespace.list:
            self.list_tasks()
        elif namespace.task is not None:
            self.run_task(
                task_name=namespace.task,
                args=namespace.args,
                context=context,
            )
        else:
            self.console.print(self.get_usage())
        self.parser.exit()

    def get_config(self, **kwargs):  # mostly so that we can mock it
        """Load the configuration."""
        return config.CliConfig(**kwargs)

    def suggest_autocompletion_bash(self):
        """Suggest autocompletion for bash."""
        program = os.path.basename(sys.argv[0])
        self.console.print("Add the following to ~/.bashrc or ~/.bash_profile:")
        self.console.print(
            f'eval "$(register-python-argcomplete {program})"',
            style="bold green",
        )

    def suggest_autocompletion_zsh(self):
        """Suggest autocompletion for zsh."""
        program = os.path.basename(sys.argv[0])
        self.console.print("Add the following to ~/.zshrc:")
        self.console.print(
            f'eval "$(register-python-argcomplete {program})"',
            style="bold green",
        )

    def list_tasks(self):
        """List the available tasks."""
        import rich.text
        import rich.tree

        tree = rich.tree.Tree(
            "Available tasks:", style="bold green", guide_style="info"
        )
        node_by_namespace = {}
        for task_path, task in sorted(self.root_namespace.items(), key=lambda x: x[0]):
            if ":" in task_path:
                namespace, task_name = task_path.rsplit(":", 1)
            else:
                task_name = task_path
                namespace = ""

            task_info = rich.text.Text(task_name, style="info")
            short_help = task.get_short_help()
            if short_help:
                task_info.append(f"\n  {short_help}", style="green")
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
        load_tasks_from_module(module, namespace=self.root_namespace)

    def get_usage(self) -> str:
        """Get the usage message."""
        return self.parser.format_usage()

    def get_task(self, task_name: str, *, context: Context) -> quickie.Task:
        """Get a task by name."""
        task_class = self.root_namespace.get_task_class(task_name)
        return task_class(name=task_name, context=context)

    def run_task(self, task_name: str, *, args, context: Context):
        """Run a task."""
        task = self.get_task(task_name, context=context)
        return task.parse_and_run(args)
