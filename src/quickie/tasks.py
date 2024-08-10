"""Base classes for tasks.

Tasks are the main building blocks of quickie. They are like self-contained
programs that can be run from the command line. They can be used to run
commands, or to run other tasks. They can also be used to group other tasks
together.
"""

import argparse
import os
import typing

from classoptions import ClassOptionsMetaclass
from rich.prompt import Confirm, Prompt

from .context import Context

MAX_SHORT_HELP_LENGTH = 50

# Because vscode currently complains about type[Task]
TaskType: typing.TypeAlias = type["Task"]


class TaskMeta(ClassOptionsMetaclass):
    """Metaclass for tasks."""

    def __new__(mcs, name, bases, attrs):  # noqa: D102
        cls = super().__new__(mcs, name, bases, attrs)
        default_meta_attr_keys = {
            o for o in dir(cls.DefaultMeta) if not o.startswith("__")
        }
        meta_attr_keys = {o for o in dir(cls._meta) if not o.startswith("__")}
        invalid_keys = meta_attr_keys - default_meta_attr_keys
        if invalid_keys:
            raise AttributeError(
                f"Invalid options in Meta for {cls}: {', '.join(invalid_keys)}. "
                f"Valid options are: {', '.join(default_meta_attr_keys)}"
            )
        if cls._meta.abstract:
            return cls
        if not cls._meta.alias:
            cls._meta.alias = name.lower()

        if cls.__doc__ and not cls._meta.abstract and not cls._meta.help:
            cls._meta.help = cls.__doc__
            short_help = cls.__doc__.split("\n")[0]
            if len(short_help) > MAX_SHORT_HELP_LENGTH:
                short_help = short_help[:MAX_SHORT_HELP_LENGTH] + "..."
            cls._meta.short_help = short_help
        return cls


class Task(metaclass=TaskMeta):
    """Base class for all tasks."""

    class DefaultMeta:
        alias: str | typing.Iterable[str] = None
        allow_unknown_args = False
        abstract = False
        help: str | None = None
        short_help: str | None = None

    _meta: DefaultMeta

    class Meta:
        abstract = True

    def __init__(
        self,
        name=None,
        *,
        context: Context | None = None,
    ):
        """Initialize the task.

        Args:
            name: The name of the task.
            context: The context of the task. To avoid side effects, a shallow
                copy is made.
        """
        # We default to the class name in case the task was not called
        # from the CLI
        self.name = name or self.__class__.__name__
        self.context = context.copy()

        self.parser = self.get_parser()
        self.add_args(self.parser)

    @property
    def console(self):
        """Get the console."""
        return self.context.console

    def print(self, *args, **kwargs):
        """Print a line."""
        self.console.print(*args, **kwargs)

    def print_error(self, *args, **kwargs):
        """Print an error message."""
        kwargs.setdefault("style", "error")
        self.print(*args, **kwargs)

    def print_success(self, *args, **kwargs):
        """Print a success message."""
        kwargs.setdefault("style", "success")
        self.print(*args, **kwargs)

    def print_warning(self, *args, **kwargs):
        """Print a warning message."""
        kwargs.setdefault("style", "warning")
        self.print(*args, **kwargs)

    def print_info(self, *args, **kwargs):
        """Print an info message."""
        kwargs.setdefault("style", "info")
        self.print(*args, **kwargs)

    def prompt(  # noqa: PLR0913
        self,
        prompt,
        *,
        password: bool = False,
        choices: list[str] | None = None,
        show_default: bool = True,
        show_choices: bool = True,
        default: typing.Any = ...,
    ) -> str:
        """Prompt the user for input.

        Args:
            prompt: The prompt message.
            password: Whether to hide the input.
            choices: List of choices.
            show_default: Whether to show the default value.
            show_choices: Whether to show the choices.
            default: The default value.
        """
        return Prompt.ask(
            prompt,
            console=self.console,
            password=password,
            choices=choices,
            show_default=show_default,
            show_choices=show_choices,
            default=default,
        )

    def confirm(self, prompt, default: bool = False) -> bool:
        """Prompt the user for confirmation.

        Args:
            prompt: The prompt message.
            default: The default value.
        """
        return Confirm.ask(prompt, console=self.console, default=default)

    def get_parser(self, **kwargs) -> argparse.ArgumentParser:
        """Get the parser for the task.

        The following keyword arguments are passed to the parser by default:
        - prog: The name of the task.
        - description: The docstring of the task.
        - add_help: False.

        Args:
            kwargs: Extra arguments to pass to the parser.
        """
        kwargs.setdefault("prog", f"{self.context.program_name} {self.name}")
        kwargs.setdefault("description", self.__doc__)
        parser = argparse.ArgumentParser(**kwargs)
        return parser

    def add_args(self, parser: argparse.ArgumentParser):
        """Add arguments to the parser.

        This method should be overridden by subclasses to add arguments to the parser.

        Args:
            parser: The parser to add arguments to.
        """
        pass

    def parse_args(
        self,
        *,
        parser: argparse.ArgumentParser,
        args: typing.Sequence[str],
        allow_unknown_args: bool,
    ):
        """Parse arguments.

        Args:
            parser: The parser to parse arguments with.
            args: The arguments to parse.
            allow_unknown_args: Whether to allow extra arguments.

        Returns:
            A tuple in the form ``(parsed_args, extra)``. Where `parsed_args` is a
            mapping of known arguments, If `allow_unknown_args` is ``True``, `extra`
            is a tuple containing the unknown arguments, otherwise it is an empty
            tuple.
        """
        if allow_unknown_args:
            parsed_args, extra = parser.parse_known_args(args)
        else:
            parsed_args = parser.parse_args(args)
            extra = ()
        return parsed_args, extra

    def get_help(self) -> str:
        """Get the help message of the task."""
        return self.parser.format_help()

    def run(self, *args, **kwargs):
        """Run the task.

        This method should be overridden by subclasses to implement the task.

        {0}
        """
        raise NotImplementedError

    def __call__(self, args: typing.Sequence[str]):
        """Call the task.

        Args:
            args: Sequence of arguments to pass to the task.
        """
        parsed_args, extra = self.parse_args(
            parser=self.parser,
            args=args,
            allow_unknown_args=self._meta.allow_unknown_args,
        )
        return self.run(*extra, **vars(parsed_args))


class BaseSubprocessTask(Task):
    """Base class for tasks that run a subprocess."""

    cwd: str | None = None
    """The current working directory."""

    env: typing.Mapping[str, str] | None = None
    """The environment."""

    class Meta:
        abstract = True

    def get_cwd(self, *args, **kwargs) -> str:
        """Get the current working directory.

        Args:
            args: Unknown arguments.
            kwargs: Parsed known arguments.
        """
        return os.path.abspath(os.path.join(self.context.cwd, self.cwd or ""))

    def get_env(self, *args, **kwargs) -> typing.Mapping[str, str]:
        """Get the environment.

        Args:
            args: Unknown arguments.
            kwargs: Parsed known arguments.
        """
        return self.context.env | (self.env or {})


class ProgramTask(BaseSubprocessTask):
    """Base class for tasks that run a program."""

    program: str | None = None
    """The program to run."""

    program_args: typing.Sequence[str] | None = None
    """The program arguments. Defaults to the task arguments."""

    class Meta:
        abstract = True

    def get_program(self, *args, **kwargs) -> str:
        """Get the program to run.

        Args:
            args: Unknown arguments.
            kwargs: Parsed known arguments.
        """
        if self.program is None:
            raise NotImplementedError("Either set program or override get_program()")
        return self.program

    def get_program_args(self, *args, **kwargs) -> typing.Sequence[str]:
        """Get the program arguments. Defaults to the task arguments.

        Args:
            args: Unknown arguments.
            kwargs: Parsed known arguments.
        """
        return self.program_args or []

    @typing.override
    def run(self, *args, **kwargs):
        program = self.get_program(*args, **kwargs)
        program_args = self.get_program_args(*args, **kwargs)
        cwd = self.get_cwd(*args, **kwargs)
        env = self.get_env(*args, **kwargs)
        return self.run_program(program, args=program_args, cwd=cwd, env=env)

    def run_program(self, program: str, *, args: typing.Sequence[str], cwd, env):
        """Run the program.

        Args:
            program: The program to run.
            args: The program arguments.
            cwd: The current working directory.
            env: The environment.
        """
        import subprocess

        result = subprocess.run(
            [program, *args],
            check=False,
            cwd=cwd,
            env=env,
        )
        return result


class ScriptTask(BaseSubprocessTask):
    """Base class for tasks that run a script."""

    script: str | None = None

    class Meta:
        abstract = True

    def get_script(self, *args, **kwargs) -> str:
        """Get the script to run.

        Args:
            args: Unknown arguments.
            kwargs: Parsed known arguments.
        """
        if self.script is None:
            raise NotImplementedError("Either set script or override get_script()")
        return self.script

    @typing.override
    def run(self, *args, **kwargs):
        script = self.get_script(*args, **kwargs)
        cwd = self.get_cwd(*args, **kwargs)
        env = self.get_env(*args, **kwargs)
        self.run_script(script, cwd=cwd, env=env)

    def run_script(self, script: str, *, cwd, env):
        """Run the script."""
        import subprocess

        result = subprocess.run(
            script,
            shell=True,
            check=False,
            cwd=cwd,
            env=env,
        )
        return result


class _TaskGroup(Task):
    """Base class for tasks that run other tasks."""

    # TODO: Make single class that can run tasks in sequence or in parallel?

    task_classes = ()
    """The task classes to run."""

    class Meta:
        abstract = True

    def get_tasks(self, *args, **kwargs) -> typing.Sequence[Task]:
        """Get the tasks to run."""
        return [task_cls(context=self.context) for task_cls in self.task_classes]

    def run_task(self, task: Task, *args, **kwargs):
        """Run a task.

        Args:
            task: The task to run.
            args: Unknown arguments.
            kwargs: Parsed known arguments.
        """
        return task.run(*args, **kwargs)


class SerialTaskGroup(_TaskGroup):
    """Base class for tasks that run other tasks in sequence."""

    class Meta:
        abstract = True

    @typing.override
    def run(self, *args, **kwargs):
        for task in self.get_tasks(*args, **kwargs):
            self.run_task(task, *args, **kwargs)


class ThreadTaskGroup(_TaskGroup):
    """Base class for tasks that run other tasks in threads."""

    max_workers = None
    """The maximum number of workers to use."""

    class Meta:
        abstract = True

    def get_max_workers(self, *args, **kwargs) -> int | None:
        """Get the maximum number of workers to use."""
        return self.max_workers

    @typing.override
    def run(self, *args, **kwargs):
        import concurrent.futures

        tasks = self.get_tasks(*args, **kwargs)
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.get_max_workers(),
            thread_name_prefix=f"quickie-parallel-task.{self.name}",
        ) as executor:
            futures = [
                executor.submit(self.run_task, task, *args, **kwargs) for task in tasks
            ]
            for future in concurrent.futures.as_completed(futures):
                future.result()
