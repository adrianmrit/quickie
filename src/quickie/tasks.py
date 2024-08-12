"""Base classes for tasks.

Tasks are the main building blocks of quickie. They are like self-contained
programs that can be run from the command line. They can be used to run
commands, or to run other tasks. They can also be used to group other tasks
together.
"""

import argparse
import functools
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
        if cls._meta.private:
            return cls
        if not cls._meta.name:
            cls._meta.name = name.lower()

        if cls.__doc__ and not cls._meta.private and not cls._meta.help:
            cls._meta.help = cls.__doc__
            short_help = cls.__doc__.split("\n")[0]
            if len(short_help) > MAX_SHORT_HELP_LENGTH:
                short_help = short_help[:MAX_SHORT_HELP_LENGTH] + "..."
            cls._meta.short_help = short_help
        return cls


class Task(metaclass=TaskMeta):
    """Base class for all tasks."""

    class DefaultMeta:
        """Default meta options."""

        name: typing.ClassVar[str | typing.Iterable[str]] = None
        """Name to identify and invoke the task.

        Multiple names can be provided as an iterable.
        """

        extra_args: typing.ClassVar[bool] = False
        """Whether to allow extra command line arguments."""

        private = False
        """Whether the task is private

        Private tasks cannot be run from the command line, but can be used
        as base classes for other tasks, or called from other tasks.
        """

        help: str | None = None
        """Help message of the task. If not provided, the docstring is used."""

        short_help: str | None = None
        """Short help message of the task. If not provided, the first line of the
        docstring is used."""

    _meta: DefaultMeta

    class Meta:
        private = True

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
        extra_args: bool,
    ):
        """Parse arguments.

        Args:
            parser: The parser to parse arguments with.
            args: The arguments to parse.
            extra_args: Whether to allow extra arguments.

        Returns:
            A tuple in the form ``(parsed_args, extra)``. Where `parsed_args` is a
            mapping of known arguments, If `extra_args` is ``True``, `extra`
            is a tuple containing the unknown arguments, otherwise it is an empty
            tuple.
        """
        if extra_args:
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
            extra_args=self._meta.extra_args,
        )
        return self.run(*extra, **vars(parsed_args))


class BaseSubprocessTask(Task):
    """Base class for tasks that run a subprocess."""

    cwd: typing.ClassVar[str | None] = None
    """The current working directory."""

    env: typing.ClassVar[typing.Mapping[str, str] | None] = None
    """The environment."""

    class Meta:
        private = True

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


class Command(BaseSubprocessTask):
    """Base class for tasks that run a binary."""

    binary: typing.ClassVar[str | None] = None
    """The name or path of the program to run."""

    args: typing.ClassVar[typing.Sequence[str] | None] = None
    """The program arguments. Defaults to the task arguments."""

    class Meta:
        private = True

    def get_binary(self, *args, **kwargs) -> str:
        """Get the name or path of the program to run.

        Args:
            args: Unknown arguments.
            kwargs: Parsed known arguments.
        """
        if self.binary is None:
            raise NotImplementedError("Either set program or override get_program()")
        return self.binary

    def get_args(self, *args, **kwargs) -> typing.Sequence[str]:
        """Get the program arguments.

        Args:
            args: Unknown arguments.
            kwargs: Parsed known arguments.
        """
        return self.args or []

    def get_cmd(self, *args, **kwargs) -> typing.Sequence[str]:
        """Get the full command to run, as a sequence.

        The first element must be the program to run, followed by the arguments.

        Args:
            args: Unknown arguments.
            kwargs: Parsed known arguments.
        """
        program = self.get_binary(*args, **kwargs)
        program_args = self.get_args(*args, **kwargs)
        return [program, *program_args]

    @typing.override
    def run(self, *args, **kwargs):
        cmd = self.get_cmd(*args, **kwargs)
        if len(cmd) == 0:
            raise ValueError("No program to run")
        elif len(cmd) == 1:
            program = cmd[0]
            args = []
        else:
            program, *args = cmd
        cwd = self.get_cwd(*args, **kwargs)
        env = self.get_env(*args, **kwargs)
        return self.run_program(program, args=args, cwd=cwd, env=env)

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


class Script(BaseSubprocessTask):
    """Base class for tasks that run a script."""

    script: typing.ClassVar[str | None] = None

    class Meta:
        private = True

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


def partial_task[T: type[Task]](task_cls: T, *args, **kwargs) -> T:
    """Create a new Task that will be called with the given arguments by default."""

    return type(
        f"{task_cls.__name__}Partial",
        (task_cls,),
        {
            "run": functools.partialmethod(task_cls.run, *args, **kwargs),
            "Meta": task_cls.Meta,  # preserve properties
        },
    )


class _TaskGroup(Task):
    """Base class for tasks that run other tasks."""

    task_classes: typing.ClassVar[typing.Sequence[type[Task]]] = ()
    """The task classes to run."""

    class Meta:
        private = True

    def get_tasks(self, *args, **kwargs) -> typing.Iterator[type[Task]]:
        """
        Get the tasks to run.

        By default returns an instance of each task class in task classes, with
        Returns:
            A sequence of tuples in the form ``(task, args, kwargs)``.
        """
        return self.task_classes

    def run_task(self, task_cls: type[Task]):
        """Run a task."""
        # This is safer than passing the parent arguments. If need to pass
        # extra arguments, can override get_tasks and use partial_task
        return task_cls(context=self.context).run()


class Group(_TaskGroup):
    """Base class for tasks that run other tasks in sequence."""

    class Meta:
        private = True

    @typing.override
    def run(self, *args, **kwargs):
        for task_cls in self.get_tasks(*args, **kwargs):
            self.run_task(task_cls)


class ThreadGroup(_TaskGroup):
    """Base class for tasks that run other tasks in threads."""

    max_workers = None
    """The maximum number of workers to use."""

    class Meta:
        private = True

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
            futures = [executor.submit(self.run_task, task) for task in tasks]
            for future in concurrent.futures.as_completed(futures):
                future.result()
