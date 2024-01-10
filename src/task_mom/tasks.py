"""Base classes for tasks.

Tasks are the main building blocks of task-mom. They are like self-contained
programs that can be run from the command line. They can be used to run
commands, or to run other tasks. They can also be used to group other tasks
together.
"""
import abc
import argparse
import os
import typing

from .context import Context, GlobalContext

# Because vscode currently complains about type[Task]
TaskType: typing.TypeAlias = type["Task"]


class NamespaceABC(abc.ABC):
    """Abstract base class for namespaces."""

    @abc.abstractmethod
    def get_store_ptr(self) -> typing.MutableMapping[str, TaskType]:
        """Get the store of tasks."""

    def register[
        T: TaskType
    ](
        self,
        cls_or_name: str | T | None = None,
        *,
        name: str | None = None,
    ) -> (
        typing.Callable[[T], T] | T
    ):
        """Register a task class."""
        if isinstance(cls_or_name, str) or cls_or_name is None:
            if name is None:
                name = cls_or_name

            def function(cls):
                self.register(cls, name=name)
                return cls

            return function
        else:
            # TODO: Check if issubclass(cls_or_name, Task)
            name = name or cls_or_name.__name__.lower()
            name = self.namespace_name(name)
            return self._store(cls_or_name, name=name)

    def _store[T: TaskType](self, cls: T, *, name: str) -> T:
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

    def __init__(self, name: str, *, parent: NamespaceABC | None = None):
        """Initialize the namespace.

        Args:
            name: The namespace name.
            separator: The separator to use when referring to tasks in the
                namespace.
            parent: The parent namespace.
        """
        self._namespace = name

        if parent is None:
            self._parent = global_namespace
        else:
            self._parent = parent

    @typing.override
    def get_store_ptr(self):
        return self._parent.get_store_ptr()

    @typing.override
    def namespace_name(self, name: str) -> str:
        name = f"{self._namespace}:{name}"
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
        if context is None:
            self.context = GlobalContext.get().copy()
        else:
            self.context = context.copy()

        self.parser = self.get_parser()
        self.add_args(self.parser)

    def writeln(self, content: str):
        """Write a line to stdout."""
        self.context.stdout.write(content + "\n")

    def errorln(self, content: str):
        """Write a line to stderr."""
        self.context.stderr.write(content + "\n")

    def input(self, prompt: str, required=True) -> str:
        """Prompt the user for input.

        Args:
            prompt: The prompt to show to the user. Note that no newline or
                ":" is added.
            required: Whether the input is required. If ``False``, an empty
                string can be returned.
        """
        result = ""
        while not result:
            self.context.stdout.write(prompt)
            self.context.stdout.flush()
            result = self.context.stdin.readline().rstrip("\n")
            if not result and not required:
                return result
        return result

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
            parser=self.parser, args=args, allow_unknown_args=self.allow_unknown_args
        )
        return self.run(*extra, **vars(parsed_args))


class BaseSubprocessTask(Task):
    """Base class for tasks that run a subprocess."""

    cwd: str | None = None
    """The current working directory."""

    env: typing.Mapping[str, str] | None = None
    """The environment."""

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
            stdout=self.context.stdout,
            stderr=self.context.stderr,
            stdin=self.context.stdin,
        )
        return result


class ScriptTask(BaseSubprocessTask):
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
            stdout=self.context.stdout,
            stderr=self.context.stderr,
            stdin=self.context.stdin,
        )
        return result


class _TaskGroup(Task):
    """Base class for tasks that run other tasks."""

    # TODO: Make single class that can run tasks in sequence or in parallel?

    task_classes = ()
    """The task classes to run."""

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

    @typing.override
    def run(self, *args, **kwargs):
        for task in self.get_tasks(*args, **kwargs):
            self.run_task(task, *args, **kwargs)


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
            futures = [
                executor.submit(self.run_task, task, *args, **kwargs) for task in tasks
            ]
            for future in concurrent.futures.as_completed(futures):
                future.result()
