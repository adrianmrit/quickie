"""Base classes for tasks.

Tasks are the main building blocks of task-mom. They are like self-contained
programs that can be run from the command line. They can be used to run
commands, or to run other tasks. They can also be used to group other tasks
together.
"""
import abc
import argparse
import sys
import typing


class NamespaceABC(abc.ABC):
    """Abstract base class for namespaces."""

    @abc.abstractmethod
    def get_store_ptr(self) -> typing.MutableMapping[str, type["Task"]]:
        """Get the store of tasks."""

    def register[
        T: type[Task]
    ](
        self,
        __cls_or_name=None,
        *,
        name: str | None = None,
    ) -> (
        typing.Callable[[T], T] | T
    ):
        """Register a task class."""
        # Handle the case where the decorator is used as `@register("name")`
        if isinstance(__cls_or_name, str):
            if name is not None:
                raise TypeError("Expected a Task class, got a string instead")
            return self.register(name=__cls_or_name)

        # Handle the case where it is used as a decorator
        if __cls_or_name is None:

            def function(cls):
                self.register(cls, name=name)
                return cls

            return function

        # Base case
        cls: T = __cls_or_name
        name = name or cls.__name__.lower()
        name = self.namespace_name(name)

        return self._store(cls, name=name)

    def _store[T: type[Task]](self, cls: T, *, name: str) -> T:
        """Store a task class."""
        store = self.get_store_ptr()
        store[name] = cls
        return cls

    def namespace_name(self, name: str) -> str:
        """Modify the name of a task."""
        return name

    @abc.abstractmethod
    def get_task_class(self, name: str) -> type["Task"]:
        """Get a task class by name."""


class _GlobalNamespace(NamespaceABC):
    def __init__(self):
        self._internal_namespace = {}

    @typing.override
    def get_store_ptr(self):
        return self._internal_namespace

    @typing.override
    def get_task_class(self, name: str) -> type["Task"]:
        return self._internal_namespace[name]


global_namespace = _GlobalNamespace()
"""The global namespace.

This namespace is used to register tasks that are available globally.
"""

register = global_namespace.register
"""Decorator to register a task class.

Same as `global_namespace.register`.

Example:
    >>> from task_mom import tasks
    >>> @register
    >>> class MyTask(Task):
    >>>     pass
    >>>
    >>> @register(name="mytask_alias")
    >>> @register(name="mytask")  # equivalent to `@register`
    >>> class MyTask(Task):
    >>>     pass
"""

get_task_class = global_namespace.get_task_class
"""Get a task class by name.

Same as `global_namespace.get_task`.

Example:
    >>> from task_mom import tasks
    >>> @register
    >>> class MyTask(Task):
    >>>     pass
    >>>
    >>> task = get_task_class("mytask")
    >>> assert task is MyTask
"""


class Namespace(NamespaceABC):
    """Namespace for tasks.

    Namespaces can be used to group tasks together. They can be used to
    organize tasks by their functionality, or by the project they belong to.

    Namespaces can be nested. For example, the namespace "project" can have
    the namespace "subproject", which can have the task "task1". The task
    can be referred to as "project.subproject.task1".

    Example:
        >>> from task_mom import tasks
        >>> namespace = tasks.Namespace("project")
        >>>
        >>> # Task is available as "project.task1"
        >>> @namespace.register
        >>> # Also available as "task1"
        >>> @tasks.register
        >>> class Task1(tasks.Task):
        >>>     pass
        >>>
        >>> @namespace.register(name="task2")
        >>> class Task2(tasks.Task):
        >>>     pass
        >>>
        >>> subnamespace = tasks.Namespace("subproject1", parent=namespace)
        >>>
        >>> # Task is available as "project1.subproject1.task3"
        >>> @subnamespace.register
        >>> class Task3(Task):
        >>>     pass
        >>>
        >>> namespace.register(subnamespace)
    """

    def __init__(self, name: str, *, separator=".", parent: NamespaceABC | None = None):
        """Initialize the namespace.

        Args:
            name: The namespace name.
            separator: The separator to use when referring to tasks in the
                namespace.
            parent: The parent namespace.
        """
        self._namespace = name
        self._separator = separator

        if parent is None:
            self._parent = global_namespace
        else:
            self._parent = parent

    @typing.override
    def get_store_ptr(self):
        return self._parent.get_store_ptr()

    @typing.override
    def namespace_name(self, name: str) -> str:
        name = f"{self._namespace}{self._separator}{name}"
        return self._parent.namespace_name(name)

    @typing.override
    def get_task_class(self, name: str) -> type["Task"]:
        """Get a task class by name, relative to the namespace.

        Args:
            name: The name of the task.

        Returns:
            The task class.
        """
        full_name = self.namespace_name(name)
        return self.get_store_ptr()[full_name]


def allow_unknown_args(cls):
    """Decorator to allow unknown arguments.

    This decorator can be used to allow extra arguments to be passed to the
    task. This is useful for tasks that run other programs, since they can
    pass the arguments to the program.

    Example:
        >>> from task_mom import tasks
        >>>
        >>> @tasks.allow_unknown_args
        >>> class MyTask(tasks.Task):
        >>>     def run(self, *args, **kwargs):
        >>>         return args, kwargs
        >>>
        >>> task = MyTask()
        >>> task(["--hello", "world", "extra", "args"])
        (("extra", "args"), {"hello": "world"})
    """
    cls.allow_unknown_args = True
    return cls


def disallow_unknown_args(cls):
    """Decorator to disallow unknown arguments.

    In case the task inherits from a task that allows unknown arguments, this
    decorator can be used to disallow them.
    """
    cls.allow_unknown_args = False
    return cls


class Task:
    """Base class for all tasks."""

    allow_unknown_args = False
    """Whether to allow extra arguments."""

    def __init__(
        self,
        name=None,
        *,
        stdout: typing.TextIO | None = None,
        stderr: typing.TextIO | None = None,
        stdin: typing.TextIO | None = None,
    ):
        """Initialize the task.

        Args:
            name: The name of the task.
            stdout: The stdout stream.
            stderr: The stderr stream.
            stdin: The stdin stream.
        """
        # We default to the class name in case the task was not called
        # from the CLI
        self.name = name or self.__class__.__name__
        self.parser = self.get_parser()
        self.add_arguments(self.parser)

        if stdout is None:
            stdout = sys.stdout
        if stderr is None:
            stderr = sys.stderr
        if stdin is None:
            stdin = sys.stdin

        self.stdout = stdout
        self.stderr = stderr
        self.stdin = stdin

    def get_parser(self, **kwargs) -> argparse.ArgumentParser:
        """Get the parser for the task.

        The following keyword arguments are passed to the parser by default:
        - prog: The name of the task.
        - description: The docstring of the task.
        - add_help: False.

        Args:
            kwargs: Extra arguments to pass to the parser.
        """
        kwargs.setdefault("prog", self.name)
        kwargs.setdefault("description", self.__doc__)
        kwargs.setdefault("add_help", False)
        parser = argparse.ArgumentParser(**kwargs)
        return parser

    def add_arguments(self, parser: argparse.ArgumentParser):
        """Add arguments to the parser.

        This method should be overridden by subclasses to add arguments to the parser.

        Args:
            parser: The parser to add arguments to.
        """
        pass

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
        if self.allow_unknown_args:
            parsed_args, extra = self.parser.parse_known_args(args)
        else:
            parsed_args = self.parser.parse_args(args)
            extra = ()
        return self.run(*extra, **vars(parsed_args))


class ProgramTask(Task):
    """Base class for tasks that run a program."""

    program: str | None = None
    """The program to run."""

    program_args: typing.Sequence[str] | None = None
    """The program arguments. Defaults to the task arguments."""

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
        return self.run_program(program, program_args)

    def run_program(self, program: str, args: typing.Sequence[str]):
        """Run the program.

        Args:
            program: The program to run.
            args: The program arguments.
        """
        import subprocess

        result = subprocess.run(
            [program, *args],
            check=False,
            stderr=self.stderr,
            stdout=self.stdout,
            stdin=self.stdin,
        )
        return result


class ScriptTask(Task):
    """Base class for tasks that run a script."""

    script: str | None = None

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
        self.run_script(script)

    def run_script(self, script: str):
        """Run the script."""
        import subprocess

        result = subprocess.run(
            script,
            shell=True,
            check=False,
            stdout=self.stdout,
            stderr=self.stderr,
            stdin=self.stdin,
        )
        return result


class _TaskGroup(Task):
    """Base class for tasks that run other tasks."""

    # TODO: Make single class that can run tasks in sequence or in parallel?

    task_classes = ()
    """The task classes to run."""

    def get_tasks(self, *args, **kwargs) -> typing.Sequence[Task]:
        """Get the tasks to run."""
        return [
            task_cls(stdout=self.stdout, stderr=self.stderr, stdin=self.stdin)
            for task_cls in self.task_classes
        ]

    def run_task(self, task: Task):
        """Run a task.

        Args:
            task: The task to run.
        """
        return task.run()


class SerialTaskGroup(_TaskGroup):
    """Base class for tasks that run other tasks in sequence."""

    @typing.override
    def run(self, *args, **kwargs):
        for task in self.get_tasks(*args, **kwargs):
            self.run_task(task)


class ThreadTaskGroup(_TaskGroup):
    """Base class for tasks that run other tasks in threads."""

    max_workers = None
    """The maximum number of workers to use."""

    def get_max_workers(self, *args, **kwargs) -> int | None:
        """Get the maximum number of workers to use."""
        return self.max_workers

    @typing.override
    def run(self, *args, **kwargs):
        import concurrent.futures

        tasks = self.get_tasks(*args, **kwargs)
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.get_max_workers(),
            thread_name_prefix=f"task-mom-parallel-task.{self.name}",
        ) as executor:
            futures = [executor.submit(self.run_task, task) for task in tasks]
            for future in concurrent.futures.as_completed(futures):
                future.result()
