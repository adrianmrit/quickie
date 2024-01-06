"""Base classes for tasks.

Tasks are the main building blocks of task-mom. They are like self-contained
programs that can be run from the command line. They can be used to run
commands, or to run other tasks. They can also be used to group other tasks
together.
"""
import abc
import argparse
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
        __cls_or_name: T | str | None = None,
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


class Task:
    """Base class for all tasks."""

    def __init__(self, name=None):
        """Initialize the task."""
        # We default to the class name in case the task was not called
        # from the CLI
        self.name = name or self.__class__.__name__
        self.parser = self.get_parser()
        self.add_arguments(self.parser)

    def get_parser(self) -> argparse.ArgumentParser:
        """Get the parser for the task."""
        parser = argparse.ArgumentParser(
            prog=self.name, description=self.__doc__, add_help=False
        )
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

    def run(self, **kwargs):
        """Run the task."""
        raise NotImplementedError

    def __call__(self, args: typing.Sequence[str]):
        """Call the task."""
        parsed_args = self.parser.parse_args(args)
        return self.run(**vars(parsed_args))


class ProgramTask(Task):
    """Base class for tasks that run a program."""

    class Meta:
        abstract = True

    program: str | None = None
    """The program to run."""

    program_args: typing.Sequence[str] | None = None
    """The program arguments. Defaults to the task arguments."""

    def get_program(self, **kwargs) -> str:
        """Get the program to run."""
        if self.program is None:
            raise NotImplementedError("Either set program or override get_program()")
        return self.program

    def get_program_args(self, **kwargs) -> typing.Sequence[str]:
        """Get the program arguments. Defaults to the task arguments."""
        return self.program_args or []

    @typing.override
    def run(self, **kwargs):
        """Run the task."""
        program = self.get_program(**kwargs)
        program_args = self.get_program_args(**kwargs)
        return self.run_program(program, program_args)

    def run_program(self, program: str, args: typing.Sequence[str]):
        """Run the program."""
        import subprocess

        result = subprocess.run([program, *args], check=False)
        return result


class ScriptTask(Task):
    """Base class for tasks that run a script."""

    class Meta:
        abstract = True

    script: str | None = None

    def get_script(self, **kwargs) -> str:
        """Get the script to run."""
        if self.script is None:
            raise NotImplementedError("Either set script or override get_script()")
        return self.script

    @typing.override
    def run(self, **kwargs):
        """Run the task."""
        script = self.get_script(**kwargs)
        self.run_script(script)

    def run_script(self, script: str):
        """Run the script."""
        import subprocess

        result = subprocess.run(script, shell=True, check=False)
        return result
