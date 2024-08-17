"""Base classes for tasks.

Tasks are the main building blocks of quickie. They are like self-contained
programs that can be run from the command line. They can be used to run
commands, or to run other tasks. They can also be used to group other tasks
together.
"""

import abc
import argparse
import contextlib
import functools
import os
import typing

from rich.prompt import Confirm, Prompt

from quickie.conditions.base import BaseCondition

from .context import Context

MAX_SHORT_HELP_LENGTH = 50

type TaskType = type[Task]
type TaskTypeOrProxy = type[Task] | _TaskProxy


class _TaskMeta(type):
    """Metaclass for tasks."""

    __qck_names: typing.Iterable[str]
    """Names it can be invoked with. Empty if private."""

    def __new__(
        mcs,
        cls_name,
        bases,
        attrs,
        *,
        name: str | typing.Iterable[str] | None = None,
        private: bool | None = None,
    ):
        if private is None:
            private = cls_name.startswith("_")

        if private:
            name = ()
        elif not name:
            name = cls_name

        if isinstance(name, str):
            name = (name,)

        # names it can be invoked with
        attrs["__qck_names"] = name
        return super().__new__(mcs, cls_name, bases, attrs)


class Task(metaclass=_TaskMeta, private=True):
    """Base class for all tasks."""

    extra_args: typing.ClassVar[bool] = False
    """Whether to allow extra command line arguments.

    If True, any unrecognized arguments are passed to the task. Otherwise, an
    error is raised if there are unknown arguments.
    """

    condition: typing.ClassVar[BaseCondition | None] = None
    """The condition to check before running the task.

    To check multiple conditions, chain them using the bitwise operators
    ``&`` (and), ``|`` (or), ``^`` (xor), and ``~`` (not).

    See :mod:`quickie.conditions` for more information.
    """

    before: typing.ClassVar[typing.Sequence[TaskType]] = ()
    """Tasks to run before this task.

    These tasks are run in the order they are defined. If one of the
    tasks fails, the remaining tasks are not run, except for cleanup tasks.
    """

    after: typing.ClassVar[typing.Sequence[TaskType]] = ()
    """Tasks to run after this task.

    These tasks are run in the order they are defined. If one of the
    tasks fails, the remaining tasks are not run, except for cleanup tasks.
    """

    cleanup: typing.ClassVar[typing.Sequence[TaskType]] = ()
    """Tasks to run at the end, even if the task, or before or after tasks fail.

    If one of the cleanup tasks fails, the remaining cleanup tasks are still run.
    """

    def __init__(
        self,
        name=None,
        *,
        context: Context,
    ):
        """Initialize the task.

        This is usually not needed, unless you want to call the task directly.

        :param name: The name of the task. Usually the name it was invoked with.
            Defaults to the class name.
        :param context: The context of the task. To avoid side effects, a shallow
            copy is made.
        """
        # We default to the class name in case the task was not called
        # from the CLI
        self.name = name or self.__class__.__name__
        self.context = context.copy()

        self.parser = self.get_parser()
        self.add_args(self.parser)

    @classmethod
    def get_help(cls) -> str:
        """Get the help message of the task."""
        return cls.__doc__ or ""

    @classmethod
    def get_short_help(cls) -> str:
        """Get the short help message of the task."""
        if not cls.__doc__:
            return ""
        summary = cls.__doc__.split("\n", 1)[0].strip()
        if len(summary) > MAX_SHORT_HELP_LENGTH:
            summary = summary[: MAX_SHORT_HELP_LENGTH - 3] + "..."
        return summary

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

        :param prompt: The prompt message.
        :param password: Whether to hide the input.
        :param choices: List of choices.
        :param show_default: Whether to show the default value.
        :param show_choices: Whether to show the choices.
        :param default: The default value.

        :return: The user input.
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

        :param prompt: The prompt message.
        :param default: The default value.

        :return: True if the user confirms, False otherwise.
        """
        return Confirm.ask(prompt, console=self.console, default=default)

    def get_parser(self, **kwargs) -> argparse.ArgumentParser:
        """Get the parser for the task.

        The following keyword arguments are passed to the parser by default:
        - prog: The name of the task.
        - description: The docstring of the task.

        :param kwargs: Extra arguments to pass to the parser.

        :return: The parser.
        """
        kwargs.setdefault("prog", f"{self.context.program_name} {self.name}")
        kwargs.setdefault("description", self.get_help())
        parser = argparse.ArgumentParser(**kwargs)
        return parser

    def add_args(self, parser: argparse.ArgumentParser):
        """Add arguments to the parser.

        This method should be overridden by subclasses to add arguments to the parser.

        :param parser: The parser to add arguments to.
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

        :param parser: The parser to parse arguments with.
        :param args: The arguments to parse.
        :param extra_args: Whether to allow extra arguments.

        :returns: A tuple in the form ``(parsed_args, extra)``. Where `parsed_args` is a
            mapping of known arguments, If `extra_args` is ``True``, `extra`
            is a tuple containing the unknown arguments, otherwise it is an empty
            tuple.
        """
        if extra_args:
            parsed_args, extra = parser.parse_known_args(args)
        else:
            parsed_args = parser.parse_args(args)
            extra = ()
        parsed_args = vars(parsed_args)
        return extra, parsed_args

    def _resolve_related(self, task_cls):
        """Get the task class."""
        if isinstance(task_cls, str):
            return self.context.namespace.get_task_class(task_cls)
        return task_cls

    def get_before(self, *args, **kwargs) -> typing.Iterator[TaskType]:
        """Get the tasks to run before this task.

        You may override this method to customize the behavior.
        or to forward extra arguments to the tasks.

        :param args: Unknown arguments.
        :param kwargs: Parsed known arguments.

        :returns: An iterator of tasks to run before this task.
        """
        for before in self.before:
            yield self._resolve_related(before)

    def get_after(self, *args, **kwargs) -> typing.Iterator[TaskType]:
        """Get the tasks to run after this task.

        You may override this method to customize the behavior.
        or to forward extra arguments to the tasks.

        :param args: Unknown arguments.
        :param kwargs: Parsed known arguments.

        :returns: An iterator of tasks to run after this task.
        """
        for after in self.after:
            yield self._resolve_related(after)

    def get_cleanup(self, *args, **kwargs) -> typing.Iterator[TaskType]:
        """Get the tasks to run after this task, even if it fails.

        You may override this method to customize the behavior.
        or to forward extra arguments to the tasks.

        :param args: Unknown arguments.
        :param kwargs: Parsed known arguments.

        :returns: An iterator of tasks to run after this task, even if it fails.
        """
        for cleanup in self.cleanup:
            yield self._resolve_related(cleanup)

    def run_before(self, *args, **kwargs):
        """Run the tasks before this task.

        :param args: Unknown arguments.
        :param kwargs: Parsed known arguments.
        """
        for task_cls in self.get_before(*args, **kwargs):
            task_cls(context=self.context)()

    def run_after(self, *args, **kwargs):
        """Run the tasks after this task.

        :param args: Unknown arguments.
        :param kwargs: Parsed known arguments.
        """
        for task_cls in self.get_after(*args, **kwargs):
            task_cls(context=self.context)()

    def run_cleanup(self, *args, **kwargs):
        """Run the tasks after this task, even if it fails.

        :param args: Unknown arguments.
        :param kwargs: Parsed known arguments.
        """
        for task_cls in self.get_cleanup(*args, **kwargs):
            try:
                task_cls(context=self.context)()
            except Exception as e:
                self.print_error(f"Error running cleanup task {task_cls}: {e}")
                continue

    def condition_passes(self, *args, **kwargs):
        """Check the condition before running the task.

        :param args: Unknown arguments.
        :param kwargs: Parsed known arguments.

        :returns: True if the condition passes, False otherwise.
        """
        if self.condition is not None:
            return self.condition(self, *args, **kwargs)
        return True

    @typing.final
    def parse_and_run(self, args: typing.Sequence[str]):
        """Parse arguments and run the task.

        :param args: The arguments to parse and run the task with.

        :returns: The result of the task.
        """
        extra, parsed_args = self.parse_args(
            parser=self.parser, args=args, extra_args=self.extra_args
        )
        return self.__call__(*extra, **parsed_args)

    def run(self, *args, **kwargs):
        """Runs work related to the task, excluding before, after, and cleanup tasks.

        This method should be overridden by subclasses to implement the task.

        :param args: Unknown arguments.
        :param kwargs: Parsed known arguments.

        :returns: The result of the task.
        """
        raise NotImplementedError

    # not implemented in __call__ so that we can override it at the instance level
    @typing.final
    def full_run(self, *args, **kwargs):
        """Call the task, including before, after, and cleanup tasks.

        :param args: Unknown arguments.
        param kwargs: Parsed known arguments.

        :returns: The result of the task.
        """
        if not self.condition_passes(*args, **kwargs):
            return
        try:
            self.run_before(*args, **kwargs)
            result = self.run(*args, **kwargs)
            self.run_after(*args, **kwargs)
            return result
        finally:
            self.run_cleanup(*args, **kwargs)

    @typing.final
    def __call__(self, *args, **kwargs):
        """Convenient shortcut for :meth:`full_run`."""
        return self.full_run(*args, **kwargs)


class _BaseSubprocessTask(Task, private=True):
    """Base class for tasks that run a subprocess."""

    cwd: typing.ClassVar[str | None] = None
    """The current working directory."""

    env: typing.ClassVar[typing.Mapping[str, str] | None] = None
    """The environment."""

    def get_cwd(self, *args, **kwargs) -> str:
        """Get the current working directory.

        :param args: Unknown arguments.
        :param kwargs: Parsed known arguments.

        :returns: The current working directory.
        """
        return os.path.abspath(os.path.join(self.context.cwd, self.cwd or ""))

    def get_env(self, *args, **kwargs) -> typing.Mapping[str, str]:
        """Get the environment.

        :param args: Unknown arguments.
        :param kwargs: Parsed known arguments.

        :returns: A mapping of environment variables.
        """
        return self.context.env | (self.env or {})


class Command(_BaseSubprocessTask, private=True):
    """Base class for tasks that run a binary."""

    binary: typing.ClassVar[str | None] = None
    """The name or path of the program to run."""

    args: typing.ClassVar[typing.Sequence[str] | None] = None
    """The program arguments. Defaults to the task arguments."""

    def get_binary(self, *args, **kwargs) -> str:
        """Get the name or path of the program to run.

        :param args: Unknown arguments.
        :param kwargs: Parsed known arguments.

        :returns: The name or path of the program to run.
        """
        if self.binary is None:
            raise NotImplementedError("Either set program or override get_program()")
        return self.binary

    def get_args(self, *args, **kwargs) -> typing.Sequence[str]:
        """Get the program arguments.

        :param args: Unknown arguments.
        :param kwargs: Parsed known arguments.

        :returns: The program arguments.
        """
        return self.args or []

    def get_cmd(self, *args, **kwargs) -> typing.Sequence[str]:
        """Get the full command to run, as a sequence.

        The first element must be the program to run, followed by the arguments.

        :param args: Unknown arguments.
        :param kwargs: Parsed known arguments.

        :returns: A sequence in the form [program, *args].
        """
        program = self.get_binary(*args, **kwargs)
        program_args = self.get_args(*args, **kwargs)
        return [program, *program_args]

    @typing.final
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
        return self._run_program(program, args=args, cwd=cwd, env=env)

    def _run_program(self, program: str, *, args: typing.Sequence[str], cwd, env):
        """Run the program.

        :param program: The program to run.
        :param args: The program arguments.
        :param cwd: The current working directory.
        :param env: A mapping of environment variables.

        :returns: The result of the program.
        """
        import subprocess

        # TODO: Raise error if code is not 0, or expected value
        result = subprocess.run(
            [program, *args],
            check=False,
            cwd=cwd,
            env=env,
        )
        return result


class Script(_BaseSubprocessTask, private=True):
    """Base class for tasks that run a script."""

    script: typing.ClassVar[str | None] = None

    def get_script(self, *args, **kwargs) -> str:
        """Get the script to run.

        :param args: Unknown arguments.
        :param kwargs: Parsed known arguments.

        :returns: The script to run.
        """
        if self.script is None:
            raise NotImplementedError("Either set script or override get_script()")
        return self.script

    @typing.final
    @typing.override
    def run(self, *args, **kwargs):
        script = self.get_script(*args, **kwargs)
        cwd = self.get_cwd(*args, **kwargs)
        env = self.get_env(*args, **kwargs)
        self._run_script(script, cwd=cwd, env=env)

    def _run_script(self, script: str, *, cwd, env):
        """Run the script."""
        import subprocess

        # TODO: Raise error if code is not 0, or expected value
        result = subprocess.run(
            script,
            shell=True,
            check=False,
            cwd=cwd,
            env=env,
        )
        return result


class _TaskProxy(abc.ABC):
    """A proxy for tasks that resolves the task class when called."""

    @abc.abstractmethod
    def resolve_task_cls(self, context: Context) -> TaskType:
        """Resolve the task class."""
        pass  # pragma: no cover

    def __call__(self, *args, context: Context, **kwargs) -> Task:
        """Resolves and initializes the task class.

        This allows to use the same interface as when initializing a task class.
        """
        task_cls = self.resolve_task_cls(context)
        return task_cls(*args, context=context, **kwargs)


class _LazyTaskProxy(_TaskProxy):
    """Used to resolve the task class lazily."""

    def __init__(self, name: str):
        self.name = name

    @typing.override
    def resolve_task_cls(self, context: Context) -> TaskType:
        """Resolve the task class."""
        return context.namespace.get_task_class(self.name)


class _PartialTaskProxy(_TaskProxy):
    """Wrapper for partial tasks."""

    def __init__(self, task_cls: TaskTypeOrProxy, *args, **kwargs):
        self.task_cls = task_cls
        self.args = args
        self.kwargs = kwargs

    @typing.override
    def resolve_task_cls(self, context: Context) -> TaskType:
        task_cls = self.task_cls
        while isinstance(task_cls, _TaskProxy):
            task_cls = task_cls.resolve_task_cls(context)
        return task_cls

    def __call__(self, *args, **kwargs) -> Task:
        """Patch full_run to inject the arguments, and return the instance.

        This way we can inject the arguments without subclassing or modifying the
        original task class. And this also allows to use the same interface as when
        initializing a task class.
        """
        instance = super().__call__(*args, **kwargs)
        instance.full_run = functools.partial(  # type: ignore
            instance.full_run, *self.args, **self.kwargs
        )
        return instance


class _SuppressErrorsTaskProxy(_TaskProxy):
    """Wrapper to suppress errors for a task."""

    class suppress_decorator(contextlib.ContextDecorator, contextlib.suppress):
        pass

    def __init__(self, task_cls: TaskTypeOrProxy, *exceptions: type[Exception]):
        self.task_cls = task_cls
        self.exceptions = exceptions or (Exception,)

    @typing.override
    def resolve_task_cls(self, context: Context) -> TaskType:
        task_cls = self.task_cls
        while isinstance(task_cls, _TaskProxy):
            task_cls = task_cls.resolve_task_cls(context)
        return task_cls  # type: ignore

    def __call__(self, *args, **kwargs) -> Task:
        """Patches full_run to ignore errors, and returns the instance."""
        instance = super().__call__(*args, **kwargs)
        instance.full_run = self.suppress_decorator(*self.exceptions)(instance.full_run)  # type: ignore
        return instance


def lazy_task(name: str) -> TaskTypeOrProxy:
    """Loads a task lazily by name.

    This is useful in cases where the task is not yet defined, or to avoid circular
    imports.

    Note that the task must be registered in the namespace before running it. Thus
    cannot lazily load tasks from external unimported modules.

    :param name: The name of the task.

    :returns: A lazy task proxy.
    """
    return _LazyTaskProxy(name)


def partial_task(task_cls: TaskTypeOrProxy | str, *args, **kwargs) -> _PartialTaskProxy:
    """Wraps a task class with partial arguments.

    This is useful when you want to inject arguments to a task without subclassing or
    modifying the original task class.

    :param task_cls: The task class or lazy task to wrap.
    :param args: The arguments to inject.
    :param kwargs: The keyword arguments to inject.

    :returns: A partial task proxy.
    """
    if isinstance(task_cls, str):
        task_cls = lazy_task(task_cls)
    return _PartialTaskProxy(task_cls, *args, **kwargs)


def suppressed_task(
    task_cls: TaskTypeOrProxy | str, *exceptions: type[Exception]
) -> _SuppressErrorsTaskProxy:
    """Wraps a task class to silently suppress errors.

    :param task_cls: The task class or lazy task to wrap.
    :param exceptions: The exceptions to suppress. While not required, it is recommended
        to specify the exceptions to suppress to avoid hiding unexpected errors.
    """
    if isinstance(task_cls, str):
        task_cls = lazy_task(task_cls)
    return _SuppressErrorsTaskProxy(task_cls, *exceptions)


class _TaskGroup(Task, private=True):
    """Base class for tasks that run other tasks."""

    task_classes: typing.ClassVar[typing.Sequence[TaskType | str]] = ()
    """The task classes to run."""

    def get_tasks(self, *args, **kwargs) -> typing.Iterable[TaskType]:
        """Get the tasks to run.

        You may override this method to customize the behavior.
        or to forward extra arguments to the tasks.

        :param args: Unknown arguments.
        :param kwargs: Parsed known arguments.

        :returns: An iterator of tasks to run.
        """
        for task_cls in self.task_classes:
            yield self._resolve_related(task_cls)

    def _run_task(self, task_cls: TaskType):
        """Run a task."""
        # This is safer than passing the parent arguments. If need to pass
        # extra arguments, can override get_tasks and use partial_task
        return task_cls(context=self.context).__call__()


class Group(_TaskGroup, private=True):
    """Base class for tasks that run other tasks in sequence."""

    @typing.final
    @typing.override
    def run(self, *args, **kwargs):
        for task_cls in self.get_tasks(*args, **kwargs):
            self._run_task(task_cls)


class ThreadGroup(_TaskGroup, private=True):
    """Base class for tasks that run other tasks in threads."""

    max_workers = None
    """The maximum number of workers to use."""

    def get_max_workers(self, *args, **kwargs) -> int | None:
        """Get the maximum number of workers to use.

        Unlimited by default. You may override this method to customize the behavior.

        :param args: Unknown arguments.
        :param kwargs: Parsed known arguments.

        :returns: The maximum number of workers to use.
        """
        return self.max_workers

    @typing.final
    @typing.override
    def run(self, *args, **kwargs):
        import concurrent.futures

        tasks = self.get_tasks(*args, **kwargs)
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.get_max_workers(),
            thread_name_prefix=f"quickie-parallel-task.{self.name}",
        ) as executor:
            futures = [executor.submit(self._run_task, task) for task in tasks]
            for future in concurrent.futures.as_completed(futures):
                future.result()
