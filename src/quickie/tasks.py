"""Base classes for tasks.

Tasks are the main building blocks of quickie. They are like self-contained
programs that can be run from the command line. They can be used to run
commands, or to run other tasks. They can also be used to group other tasks
together.
"""

import argparse
import functools
import os
from pathlib import Path
import re
import shlex
import typing

from quickie.conditions.base import BaseCondition
from quickie.errors import Skip
from quickie.config import app
from quickie.utils.argparser import Arg


MAX_SHORT_HELP_LENGTH = 50


class Task:
    """Base class for all tasks."""

    args: typing.Sequence[Arg | str | typing.Sequence[str]] = ()
    """Arguments for the task.

    This is a sequence of either:
        - strings
        - sequence of strings
        - :class:`~quickie.utils.argparser.Arg` objects.

    If a string or a sequence of strings is provided, it is converted to an
    :class:`~quickie.utils.argparser.Arg` object, by passing the string(s) as
    positional arguments to the constructor.
    """

    extra_args: bool = False
    """Whether to allow extra command line arguments.

    If True, any unrecognized arguments are passed to the task. Otherwise, an
    error is raised if there are unknown arguments.
    """

    condition: BaseCondition | None = None
    """The condition to check before running the task.

    To check multiple conditions, chain them using the bitwise operators
    ``&`` (and), ``|`` (or), ``^`` (xor), and ``~`` (not).

    See :mod:`quickie.conditions` for more information.
    """

    before: typing.Sequence[typing.Callable] = ()
    """Tasks to run before this task.

    These tasks are run in the order they are defined. If one of the
    tasks fails, the remaining tasks are not run, except for cleanup tasks.
    """

    after: typing.Sequence[typing.Callable] = ()
    """Tasks to run after this task.

    These tasks are run in the order they are defined. If one of the
    tasks fails, the remaining tasks are not run, except for cleanup tasks.
    """

    cleanup: typing.Sequence[typing.Callable] = ()
    """Tasks to run at the end, even if the task, or before or after tasks fail.

    If one of the cleanup tasks fails, the remaining cleanup tasks are still run.
    """

    def __init__(  # noqa: PLR0913
        self,
        name: str | None = None,
        *,
        aliases: typing.Sequence[str] | None = None,
        private: bool = False,
        defined_from: type | typing.Callable | None = None,
        args: typing.Sequence[Arg | str | typing.Sequence[str]] | None = None,
        extra_args: bool | None = None,
        condition: BaseCondition | None = None,
        before: typing.Sequence[typing.Callable] | None = None,
        after: typing.Sequence[typing.Callable] | None = None,
        cleanup: typing.Sequence[typing.Callable] | None = None,
    ):
        """Initialize the task.

        :param name: The name it can be invoked with. If not provided, it defaults to
            the class name.
        :param aliases: Alternative names it can be invoked with..
        :param defined_from: The obj (class or function) where the task was defined.
            If not provided, and the task is not private, it defaults to the class
            itself.
        :param private: Whether the task is private. If not provided, it is private if
            the class name starts with an underscore.
        :param args: The arguments for the task. If not provided, it defaults to the
            class attribute :attr:`args`.
        :param extra_args: Whether to allow extra command line arguments. If not
            provided, it defaults to the class attribute :attr:`extra_args`.
        :param condition: The condition to check before running the task. If not
            provided, it defaults to the class attribute :attr:`condition`.
        :param before: The tasks to run before this task. If not provided, it defaults
            to the class attribute :attr:`before`.
        :param after: The tasks to run after this task. If not provided, it defaults
            to the class attribute :attr:`after`.
        :param cleanup: The tasks to run at the end, even if the task, or before or
            after tasks fail. If not provided, it defaults to the class attribute
            :attr:`cleanup`.
        """
        self.name = name or self.__class__.__name__
        self.aliases = aliases or ()
        self.private = private

        self.defined_from = defined_from if defined_from is not None else self.__class__
        self.args = args if args is not None else self.args
        self.extra_args = extra_args if extra_args is not None else self.extra_args
        self.condition = condition if condition is not None else self.condition
        self.before = before if before is not None else self.before
        self.after = after if after is not None else self.after
        self.cleanup = cleanup if cleanup is not None else self.cleanup

    def _get_relative_file_location(self, basedir) -> str | None:
        """Returns the file and line number where the class was defined."""
        import inspect

        if self.defined_from is None:
            return None
        file = inspect.getfile(self.defined_from)
        source_lines = inspect.getsourcelines(self.defined_from)
        relative_path = os.path.relpath(file, basedir)
        return f"{relative_path}:{source_lines[1]}"

    @functools.cached_property
    def parser(self) -> argparse.ArgumentParser:
        """Parser for the task."""
        parser = self.get_parser()
        self.add_args(parser)
        return parser

    def get_help(self) -> str:
        """Get the help message of the task."""
        if self.__doc__:
            return self.__doc__
        if self.defined_from is not None:
            return self.defined_from.__doc__ or ""
        return ""

    def get_short_help(self) -> str:
        """Get the short help message of the task."""
        summary = self.get_help().split("\n\n", 1)[0].strip()
        summary = re.sub(r"\s+", " ", summary)
        if len(summary) > MAX_SHORT_HELP_LENGTH:
            summary = summary[: MAX_SHORT_HELP_LENGTH - 3] + "..."
        return summary

    def get_parser(
        self, *, name: str | None = None, **kwargs
    ) -> argparse.ArgumentParser:
        """Get the parser for the task.

        The following keyword arguments are passed to the parser by default:
        - prog: The name of the task.
        - description: The docstring of the task.

        :param kwargs: Extra arguments to pass to the parser.

        :return: The parser.
        """
        if "prog" not in kwargs:
            kwargs["prog"] = name or self.name
        if "description" not in kwargs:
            kwargs["description"] = self.get_help()
        parser = argparse.ArgumentParser(**kwargs)
        return parser

    def add_args(self, parser: argparse.ArgumentParser):
        """Add arguments to the parser.

        This method should be overridden by subclasses to add arguments to the parser.

        :param parser: The parser to add arguments to.
        """
        for a in self.args:
            if isinstance(a, str):
                arg = Arg(a)
            elif isinstance(a, typing.Sequence):
                arg = Arg(*a)
            elif isinstance(a, Arg):
                arg = a
            else:
                raise TypeError(f"Invalid argument type: {type(arg)}")
            arg.add(parser)

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
            return app.tasks[task_cls]
        return task_cls

    def get_before(self, *args, **kwargs) -> typing.Iterator["Task"]:
        """Get the tasks to run before this task.

        You may override this method to customize the behavior.
        or to forward extra arguments to the tasks.

        :param args: Unknown arguments.
        :param kwargs: Parsed known arguments.

        :returns: An iterator of tasks to run before this task.
        """
        for before in self.before:
            yield self._resolve_related(before)

    def get_after(self, *args, **kwargs) -> typing.Iterator["Task"]:
        """Get the tasks to run after this task.

        You may override this method to customize the behavior.
        or to forward extra arguments to the tasks.

        :param args: Unknown arguments.
        :param kwargs: Parsed known arguments.

        :returns: An iterator of tasks to run after this task.
        """
        for after in self.after:
            yield self._resolve_related(after)

    def get_cleanup(self, *args, **kwargs) -> typing.Iterator["Task"]:
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
        for task in self.get_before(*args, **kwargs):
            task()

    def run_after(self, *args, **kwargs):
        """Run the tasks after this task.

        :param args: Unknown arguments.
        :param kwargs: Parsed known arguments.
        """
        for task in self.get_after(*args, **kwargs):
            task()

    def run_cleanup(self, *args, **kwargs):
        """Run the tasks after this task, even if it fails.

        :param args: Unknown arguments.
        :param kwargs: Parsed known arguments.
        """
        for task in self.get_cleanup(*args, **kwargs):
            try:
                task()
            except Exception as e:
                app.logger.error(f"Error running cleanup task {task}: {e}")
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
        if extra and extra[0] == "--":
            # -- Can be used to separate task args from extra arguments, but the parser
            # does not remove it automatically.
            # We only remove the first occurrence of --, so if there are multiple
            # occurrences, the rest are passed to the task.
            extra = extra[1:]
        return self.__call__(*extra, **parsed_args)

    def run(self, *args, **kwargs):
        """Runs work related to the task, excluding before, after, and cleanup tasks.

        This method should be overridden by subclasses to implement the task.

        :param args: Unknown arguments.
        :param kwargs: Parsed known arguments.

        :returns: The result of the task.
        """
        raise NotImplementedError

    def log_task_execution(self, *args, **kwargs):
        """Log information about the task execution."""
        from quickie import app

        # Log task name and arguments
        app.logger.info(f"Executing task: [info]{self.name}[/info]")

    def log_task_execution_details(self, *args, **kwargs):
        """Log details about the task execution."""
        pass

    # not implemented in __call__ so that we can override it at the instance level
    @typing.final
    def full_run(self, *args, **kwargs):
        """Call the task, including before, after, and cleanup tasks.

        :param args: Unknown arguments.
        :param kwargs: Parsed known arguments.

        :returns: The result of the task.
        """
        from quickie import app

        if not self.condition_passes(*args, **kwargs):
            app.logger.info(f"Skipping task {self.name}: conditions not met.")
            return
        try:
            self.run_before(*args, **kwargs)
            try:
                self.log_task_execution(*args, **kwargs)
                result = self.run(*args, **kwargs)
            except Skip as e:
                app.logger.info(f"Skipping task {self.name}: {e.message}")
                result = None
            self.run_after(*args, **kwargs)
            return result
        finally:
            self.run_cleanup(*args, **kwargs)

    @typing.final
    def __call__(self, *args, **kwargs):
        """Convenient shortcut for :meth:`full_run`."""
        return self.full_run(*args, **kwargs)


class _BaseSubprocessTask(Task):
    """Base class for tasks that run a subprocess."""

    wd: str | Path | None = None
    """The current working directory."""

    env: typing.Mapping[str, str] | None = None
    """The environment."""

    def __init__(
        self,
        *args,
        env: typing.Mapping[str, str] | None = None,
        wd: str | Path | None = None,
        **kwargs,
    ):
        """Initialize the task.

        :param args: Task instance arguments.
        :param env: The environment to use.
        :param wd: The working directory.
        :param kwargs: Task instance keyword arguments.
        """
        super().__init__(*args, **kwargs)
        self.wd = wd if wd is not None else self.wd
        self.env = env if env is not None else self.env

    def get_wd(self, *args, **kwargs) -> str:
        """Get the working directory.

        :param args: Unknown arguments.
        :param kwargs: Parsed known arguments.

        :returns: The working directory.
        """
        if self.wd is None:
            path = app.context.wd
        elif self.wd == ".":
            path = app.tasks_path.parent
            app.logger.debug(f"Using current working directory: {path}")
        elif not os.path.isabs(self.wd):
            # If the path is relative, join it with the current working directory
            # to get the absolute path.
            path = os.path.join(app.context.wd, self.wd)
        else:
            path = self.wd
        return os.path.abspath(path)

    def get_env(self, *args, **kwargs) -> typing.Mapping[str, str]:
        """Get the environment.

        :param args: Unknown arguments.
        :param kwargs: Parsed known arguments.

        :returns: A mapping of environment variables.
        """
        # Chain maps are supposed to use dicts, but we won't do any updates
        # to this dictionary. So we can allow it to be any sort of mapping.
        env = typing.cast(dict, self.env)
        return app.context.env.new_child(env).new_child()


class Command(_BaseSubprocessTask):
    """Base class for tasks that run a binary."""

    binary: str | None = None
    """The name or path of the program to run."""

    cmd_args: typing.Sequence[str] | None = None
    """The program arguments. Defaults to the task arguments."""

    def __init__(
        self,
        *args,
        binary: str | None = None,
        cmd_args: typing.Sequence[str] | None = None,
        **kwargs,
    ):
        """Initialize the task.

        :param args: Task instance arguments.
        :param kwargs: Task instance keyword arguments.
        """
        super().__init__(*args, **kwargs)
        self.binary = binary if binary is not None else self.binary
        self.cmd_args = cmd_args if cmd_args is not None else self.cmd_args

    def get_binary(self, *args, **kwargs) -> str:
        """Get the name or path of the program to run.

        :param args: Unknown arguments.
        :param kwargs: Parsed known arguments.

        :returns: The name or path of the program to run.
        """
        if self.binary is None:
            raise NotImplementedError("Either set program or override get_program()")
        return self.binary

    def get_cmd_args(self, *args, **kwargs) -> typing.Sequence[str] | str:
        """Get the program arguments.

        :param args: Unknown arguments.
        :param kwargs: Parsed known arguments.

        :returns: The program arguments.
        """
        return self.cmd_args or []

    def get_cmd(self, *args, **kwargs) -> typing.Sequence[str] | str:
        """Get the full command to run, as a sequence.

        The first element must be the program to run, followed by the arguments.

        :param args: Unknown arguments.
        :param kwargs: Parsed known arguments.

        :returns: A sequence in the form [program, *args].
        """
        program = self.get_binary(*args, **kwargs)
        program_args = self.get_cmd_args(*args, **kwargs)
        program_args = self.split_cmd_args(program_args)
        return [program, *program_args]

    def split_cmd_args(self, args: str | typing.Sequence[str]) -> typing.Sequence[str]:
        """Split the arguments string into a list of arguments.

        :param args: The arguments string.

        :returns: A list of arguments.
        """
        import shlex

        if isinstance(args, str):
            args = shlex.split(args)
        return args

    @typing.override
    def log_task_execution_details(self, program, args):
        """Log details about the task execution."""
        from quickie import app

        command = shlex.join([program, *args])
        app.logger.debug(f"Execute command: {command}")

    @typing.final
    @typing.override
    def run(self, *args, **kwargs):
        cmd = self.get_cmd(*args, **kwargs)
        cmd = self.split_cmd_args(cmd)

        if len(cmd) == 0:
            raise ValueError("No program to run")
        elif len(cmd) == 1:
            program = cmd[0]
            args = []
        else:
            program, *args = cmd
        wd = self.get_wd(*args, **kwargs)
        env = self.get_env(*args, **kwargs)
        return self._run_program(program, cmd_args=args, wd=wd, env=env)

    def _run_program(
        self,
        program: str,
        *,
        cmd_args: typing.Sequence[str],
        wd: str,
        env: typing.Mapping[str, str],
    ):
        """Run the program.

        :param program: The program to run.
        :param args: The program arguments.
        :param wd: The working directory.
        :param env: A mapping of environment variables.

        :returns: The result of the program.
        """
        import subprocess

        self.log_task_execution_details(program, cmd_args)
        result = subprocess.run(
            [program, *cmd_args],
            check=False,
            cwd=wd,
            env=env,
        )
        return result


class Script(_BaseSubprocessTask):
    """Base class for tasks that run a script."""

    script: str | None = None
    executable: str | None = None

    def __init__(
        self, *args, script: str | None = None, executable: str | None = None, **kwargs
    ):
        """Initialize the task.

        :param args: Task instance arguments.
        :param script: The script to run.
        :param executable: The executable to use to run the script.
        :param kwargs: Task instance keyword arguments.
        """
        super().__init__(*args, **kwargs)
        self.script = script if script is not None else self.script
        self.executable = executable if executable is not None else self.executable

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
        wd = self.get_wd(*args, **kwargs)
        env = self.get_env(*args, **kwargs)
        self._run_script(script, wd=wd, env=env)

    @typing.override
    def log_task_execution_details(self, script):
        """Log details about the task execution."""
        from quickie import app

        # TODO: Highlight syntax
        if self.executable:
            app.logger.info(f"Execute script: [info]{self.executable} {script}[/info]")
        else:
            app.logger.info(f"Execute script: [info]{script}[/info]")

    def _run_script(self, script: str, *, wd, env):
        """Run the script."""
        import subprocess

        # TODO: Raise error if code is not 0, or expected value
        self.log_task_execution_details(script)
        result = subprocess.run(
            script,
            shell=True,
            check=False,
            cwd=wd,
            env=env,
            executable=self.executable,
        )
        return result


class _TaskGroup(Task):
    """Base class for tasks that run other tasks."""

    tasks: typing.ClassVar[typing.Sequence["Task | str"]] = ()
    """The task classes to run."""

    def get_tasks(self, *args, **kwargs) -> typing.Iterable["Task"]:
        """Get the tasks to run.

        You may override this method to customize the behavior.
        or to forward extra arguments to the tasks.

        :param args: Unknown arguments.
        :param kwargs: Parsed known arguments.

        :returns: An iterator of tasks to run.
        """
        for task in self.tasks:
            yield self._resolve_related(task)

    def _run_task(self, task: "Task"):
        """Run a task."""
        # This is safer than passing the parent arguments. If need to pass
        # extra arguments, can override get_tasks and use functools.partial
        return task()


class Group(_TaskGroup):
    """Base class for tasks that run other tasks in sequence."""

    @typing.final
    @typing.override
    def run(self, *args, **kwargs):
        for task in self.get_tasks(*args, **kwargs):
            self._run_task(task)


class ThreadGroup(_TaskGroup):
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
