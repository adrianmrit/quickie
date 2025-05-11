"""The CLI entry of quickie."""

import os
import sys

import argcomplete
from rich import traceback

import quickie
from quickie import app
from quickie._argparser import AppArgumentParser
from quickie.errors import QuickieError, Skip, Stop


def _clean_exit(func):
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            print("Exiting due to KeyboardInterrupt.")
            sys.exit(1)

    return wrapper


@_clean_exit
def main(argv=None, *, raise_error=False, global_=False):
    """Run the CLI."""
    traceback.install(suppress=[quickie])
    main = Main(argv=argv, global_=global_)
    try:
        main()
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


@_clean_exit
def global_main(argv=None, *, raise_error=False):
    """Run the CLI with the global option."""
    main(
        argv=argv,
        raise_error=raise_error,
        global_=True,
    )


class Main:
    """Represents the CLI entry of quickie."""

    def __init__(self, *, argv=None, global_=False):  # noqa: PLR0913
        """Initialize the CLI."""
        if argv is None:
            argv = sys.argv[1:]
        self.argv = argv
        self.parser = AppArgumentParser(main=self)
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
        app.set_verbosity(namespace.verbosity)
        app.set_log_file(namespace.log_file)
        if not self.global_ and namespace.module:
            app.set_project_path(namespace.module)
        app.set_use_global(self.global_)
        # Loads tasks before completion

        if arg_complete_val:
            app.load_tasks()
            if namespace.task:
                task = self.get_task(namespace.task)
                # Update _ARGCOMPLETE to the index of the task, so that completion
                # only considers the task arguments
                os.environ["_ARGCOMPLETE"] = str(args.index(namespace.task))
                parser = task.parser
            else:
                parser = self.parser
            argcomplete.autocomplete(parser)
            sys.exit(0)

        app.logger.info(f"Running quickie {quickie.__version__}")
        if namespace.init:
            from quickie._init import init

            init(namespace.init)
        elif namespace.suggest_auto_completion:
            if namespace.suggest_auto_completion == "bash":
                self.suggest_autocompletion_bash()
            elif namespace.suggest_auto_completion == "zsh":
                self.suggest_autocompletion_zsh()
        elif namespace.list:
            app.load_tasks()
            self.list_tasks()
        elif namespace.task is not None:
            app.load_tasks()
            self.run_task(
                task_name=namespace.task,
                args=namespace.args,
            )
        else:
            app.console.print(self.get_usage())
        self.parser.exit()

    def suggest_autocompletion_bash(self):
        """Suggest autocompletion for bash."""
        program = os.path.basename(sys.argv[0])
        app.console.print("Add the following to ~/.bashrc or ~/.bash_profile:")
        app.console.print(
            f'eval "$(register-python-argcomplete {program})"',
            style="bold green",
        )

    def suggest_autocompletion_zsh(self):
        """Suggest autocompletion for zsh."""
        program = os.path.basename(sys.argv[0])
        app.console.print("Add the following to ~/.zshrc:")
        app.console.print(
            f'eval "$(register-python-argcomplete {program})"',
            style="bold green",
        )

    def list_tasks(self):
        """List the available tasks."""
        import rich.box
        import rich.table
        import rich.text

        table = rich.table.Table(title="Available tasks", box=rich.box.SIMPLE)
        table.add_column("Task", style="bold yellow")
        table.add_column("Aliases", style="bold yellow")
        table.add_column("Short Description", style="bold yellow")
        table.add_column("Location", style="bold yellow")

        # Invert the task dictionary to group by class
        names_by_task: dict[quickie.Task, list[str]] = {}
        for invocation_name, task in sorted(
            app.tasks.items(),
            key=lambda x: (
                x[1]._get_relative_file_location(os.getcwd()) or "",
                x[0].count(":"),
                x[0].split(":"),
            ),
        ):
            names_by_task.setdefault(task, []).append(invocation_name)

        for task, task_names in names_by_task.items():
            aliases = ", ".join(
                sorted(name for name in task_names if name != task.name)
            )
            rich_task_name = rich.text.Text(task.name, style="bold")
            rich_aliases = rich.text.Text(aliases, style="dim")
            task_location = rich.text.Text(
                task._get_relative_file_location(os.getcwd()) or "", style="dim"
            )
            short_help = rich.text.Text(task.get_short_help(), style="green")
            table.add_row(rich_task_name, rich_aliases, short_help, task_location)

        app.console.print(table)

    def get_usage(self) -> str:
        """Get the usage message."""
        return self.parser.format_usage()

    def get_task(self, task_name: str) -> quickie.Task:
        """Get a task by name."""
        return app.tasks[task_name]

    def run_task(self, task_name: str, *, args):
        """Run a task."""
        task = self.get_task(task_name)
        return task.parse_and_run(args)
