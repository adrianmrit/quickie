"""Base classes for tasks.

Tasks are the main building blocks of quickie. They are like self-contained
programs that can be run from the command line. They can be used to run
commands, or to run other tasks. They can also be used to group other tasks
together.
"""

import argparse
import concurrent.futures
import enum
import functools
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import threading
import time
import typing

from quickie.conditions.base import BaseCondition
from quickie.context import load_env_file
from quickie.errors import Skip, SubprocessExitCodeError, SubprocessTimeoutError
from quickie._sentinels import USE_DEFAULT, UseDefault
from quickie.config import app
from quickie.utils.argparser import Arg


MAX_SHORT_HELP_LENGTH = 50
_UNDERSCORE_SUB_REGEX = re.compile(r"_+")


def identifier_to_task_name(identifier: str) -> str:
    """Transforms a python identifier to a task name.

    This is useful to convert a class name or function name to a task name.
    The transformation is done by replacing all continuous underscores with a dash
    and converting the string to lowercase. The result is stripped of leading and
    trailing dashes.

    Example:
        >>> identifier_to_task_name("MyTask")
        "mytask"
        >>> identifier_to_task_name("My__Task_")
        "my-task"

    :param identifier: The python identifier to transform.

    :returns: The transformed task name.
    """
    return _UNDERSCORE_SUB_REGEX.sub("-", identifier).strip("-").lower()


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
        wraps: type | typing.Callable | None = None,
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
        :param wraps: The obj (class or function) where the task was defined.
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
        self.name = name or identifier_to_task_name(self.__class__.__name__)
        self.aliases = aliases or ()
        self.private = private

        while hasattr(wraps, "__wrapped__"):
            wraps = wraps.__wrapped__  # type: ignore

        self.__wrapped__ = wraps if wraps is not None else self.__class__
        self.args = args if args is not None else self.args
        self.extra_args = extra_args if extra_args is not None else self.extra_args
        self.condition = condition if condition is not None else self.condition
        self.before = before if before is not None else self.before
        self.after = after if after is not None else self.after
        self.cleanup = cleanup if cleanup is not None else self.cleanup

    def _get_relative_file_location(self, basedir) -> str | None:
        """Returns the file and line number where the class was defined."""
        import inspect

        wraps = self.__wrapped__

        # functools.wraps and functools.lru_cache will return a wrapped function
        # We want the original one to get the file and line number.
        while hasattr(wraps, "__wrapped__"):
            wraps = wraps.__wrapped__  # type: ignore

        try:
            file = inspect.getfile(wraps)
            source_lines = inspect.getsourcelines(wraps)
        except TypeError:
            return None
        else:
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
        if self.__wrapped__ is not None:
            return self.__wrapped__.__doc__ or ""
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
                raise TypeError(f"Invalid argument type: {type(a)}")
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

    def run(self, *args, **kwargs) -> typing.Any:
        """Run the main work of this task.

        Override this in subclasses to implement task logic. Return any value;
        it will be propagated to the caller of :meth:`__call__`.

        ``before``, ``after``, and ``cleanup`` phases are *not* invoked by
        this method — use :meth:`__call__` when calling a task from inside
        another task's ``run()`` to include the full lifecycle.

        :param args: Positional arguments forwarded from :meth:`__call__`.
        :param kwargs: Keyword arguments forwarded from :meth:`__call__`.

        :returns: Any value; propagated as-is to the caller.
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
    def full_run(self, *args, **kwargs) -> typing.Any:
        """Execute the full task lifecycle and return the result of :meth:`run`.

        Execution order:

        1. **condition** — if it fails, logs and returns ``None`` immediately.
        2. **before** — each task in :attr:`before` is called; return values
           are discarded.
        3. **run** — the main work; its return value is captured.
           If :exc:`~quickie.errors.Skip` is raised, the result is set to
           ``None`` and ``after`` still runs.
        4. **after** — each task in :attr:`after` is called; return values
           are discarded.
        5. **cleanup** — each task in :attr:`cleanup` is called even if an
           earlier phase raised; exceptions are logged and swallowed.

        ``before``, ``after``, and ``cleanup`` phase return values are always
        discarded.  To pass results between tasks, call them directly from
        :meth:`run` instead:

        .. code-block:: python

            class MyTask(Task):
                def run(self):
                    b_result = TaskB()()
                    return TaskC()(b_result)

        :param args: Positional arguments forwarded to each phase.
        :param kwargs: Keyword arguments forwarded to each phase.

        :returns: The return value of :meth:`run`, or ``None`` if the
            condition failed or :exc:`~quickie.errors.Skip` was raised.
        """
        from quickie import app

        if not self.condition_passes(*args, **kwargs):
            app.logger.info(f"Skipping task {self.name}: conditions not met.")
            return None
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
    def __call__(self, *args, **kwargs) -> typing.Any:
        """Invoke this task, running the full lifecycle via :meth:`full_run`.

        This is the canonical way to call a task from within another task's
        :meth:`run` method::

            class PipelineTask(Task):
                def run(self):
                    data = FetchTask()()
                    return ProcessTask()(data)

        :returns: The return value of :meth:`run`, or ``None`` if the
            condition failed or :exc:`~quickie.errors.Skip` was raised.
        """
        return self.full_run(*args, **kwargs)


class OutputMode(enum.StrEnum):
    """Controls how subprocess stdout and stderr are handled."""

    STREAM = "stream"
    """Stream output directly to the terminal (default). Output is not captured."""

    CAPTURE = "capture"
    """Capture stdout and stderr as bytes; nothing is printed to the terminal.

    The returned :class:`subprocess.CompletedProcess` will have populated
    ``.stdout`` and ``.stderr`` byte attributes.
    """

    TEE = "tee"
    """Stream output to the terminal *and* capture it as bytes.

    The returned :class:`subprocess.CompletedProcess` will have populated
    ``.stdout`` and ``.stderr`` byte attributes while output is still written
    to the terminal in real time.
    """


type OutputModeT = OutputMode | typing.Literal["stream", "capture", "tee"]
"""Accepted values for the ``output_mode`` parameter.

Either an :class:`OutputMode` member or one of the string literals
``"stream"``, ``"capture"``, or ``"tee"``.
"""


class _BaseSubprocessTask(Task):
    """Base class for tasks that run a subprocess."""

    wd: str | Path | None = None
    """The current working directory."""

    env: typing.Mapping[str, str] | None = None
    """The environment."""

    env_file: str | Path | None = None
    """Path to a ``.env`` file whose variables are merged into the environment.

    Relative paths are resolved from the quickie tasks root directory.
    Values from this file are overridden by :attr:`env`.
    """

    expected_exit_codes: typing.Sequence[int] | None = (0,)
    """Accepted subprocess exit codes."""

    timeout: float | None = None
    """Timeout in seconds for each subprocess attempt. ``None`` means no limit."""

    retries: int = 0
    """Number of additional attempts after an initial failure.

    Set to a positive integer to automatically re-run the subprocess on
    transient errors (:exc:`~quickie.errors.SubprocessExitCodeError` or
    :exc:`~quickie.errors.SubprocessTimeoutError`).
    """

    retry_delay: float = 0.0
    """Seconds to wait between retry attempts."""

    output_mode: OutputMode = OutputMode.STREAM
    """Controls how subprocess output is handled.

    - :attr:`OutputMode.STREAM` — output goes to the terminal (default).
    - :attr:`OutputMode.CAPTURE` — output is captured; terminal sees nothing.
    - :attr:`OutputMode.TEE` — output streams to the terminal *and* is captured.

    The latter two modes populate :attr:`subprocess.CompletedProcess.stdout`
    and :attr:`subprocess.CompletedProcess.stderr` as :class:`bytes` objects on
    the returned result, enabling use of subprocess output in composing tasks.
    """

    def __init__(  # noqa: PLR0913
        self,
        *args,
        env: typing.Mapping[str, str] | None = None,
        env_file: str | Path | None = None,
        wd: str | Path | None = None,
        expected_exit_codes: typing.Sequence[int] | None | UseDefault = USE_DEFAULT,
        timeout: float | None | UseDefault = USE_DEFAULT,
        retries: int | UseDefault = USE_DEFAULT,
        retry_delay: float | UseDefault = USE_DEFAULT,
        output_mode: OutputModeT | UseDefault = USE_DEFAULT,
        **kwargs,
    ):
        """Initialize the task.

        :param args: Task instance arguments.
        :param env: The environment to use.
        :param env_file: Path to a ``.env`` file.  Relative paths are resolved
            from the quickie tasks root.  Values are overridden by *env*.
        :param wd: The working directory.
        :param expected_exit_codes: Accepted subprocess exit codes.
            Pass ``None`` or ``()`` to disable validation.
        :param timeout: Timeout in seconds for each attempt. ``None`` means no limit.
        :param retries: Number of additional attempts after an initial failure.
        :param retry_delay: Seconds to wait between retry attempts.
        :param output_mode: How to handle subprocess output — ``"stream"`` (default),
            ``"capture"``, or ``"tee"``. Accepts :class:`OutputMode` values or the
            equivalent string literals.
        :param kwargs: Task instance keyword arguments.
        """
        super().__init__(*args, **kwargs)
        self.wd = wd if wd is not None else self.wd
        self.env = env if env is not None else self.env
        self.env_file = env_file if env_file is not None else self.env_file
        if expected_exit_codes is USE_DEFAULT:
            expected_exit_codes = self.expected_exit_codes
        self.expected_exit_codes = self._normalize_expected_exit_codes(
            expected_exit_codes
        )
        if timeout is USE_DEFAULT:
            timeout = self.timeout
        self.timeout = timeout
        if retries is USE_DEFAULT:
            retries = self.retries
        self.retries = retries
        if retry_delay is USE_DEFAULT:
            retry_delay = self.retry_delay
        self.retry_delay = retry_delay
        if output_mode is USE_DEFAULT:
            output_mode = self.output_mode
        self.output_mode = OutputMode(output_mode)

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
        if self.env_file is not None:
            base_dir = app.tasks_path.parent
            env_file_path = (
                os.path.join(base_dir, self.env_file)
                if not os.path.isabs(self.env_file)
                else self.env_file
            )
            file_env = typing.cast(dict, load_env_file(env_file_path))
        else:
            file_env = {}
        # Precedence (high → low): explicit env > file env > context env > OS env
        return app.context.env.new_child(file_env).new_child(env).new_child()

    def _normalize_expected_exit_codes(
        self,
        expected_exit_codes: typing.Sequence[int] | None,
    ) -> tuple[int, ...] | None:
        if not expected_exit_codes:
            return None

        normalized = tuple(expected_exit_codes)

        if not all(isinstance(code, int) for code in normalized):
            raise TypeError("expected_exit_codes values must be integers")
        return normalized

    def get_expected_exit_codes(self, *args, **kwargs) -> typing.Iterable[int] | None:
        """Get accepted subprocess exit codes."""
        return self.expected_exit_codes

    def get_timeout(self) -> float | None:
        """Get the subprocess timeout in seconds.

        :returns: The timeout value, or ``None`` for no limit.
        """
        return self.timeout

    def get_retries(self) -> int:
        """Get the number of additional retry attempts."""
        return self.retries

    def get_retry_delay(self) -> float:
        """Get the seconds to wait between retry attempts."""
        return self.retry_delay

    def validate_exit_code(
        self,
        *,
        return_code: int,
        command: str,
        expected_exit_codes: typing.Iterable[int] | None,
    ):
        """Validate the subprocess return code."""
        if not expected_exit_codes:
            return
        if return_code not in expected_exit_codes:
            raise SubprocessExitCodeError(
                task_name=self.name,
                return_code=return_code,
                command=command,
                expected_exit_codes=expected_exit_codes,
            )

    def _execute_with_retry(
        self, attempt_fn: typing.Callable[[], typing.Any]
    ) -> typing.Any:
        """Execute attempt_fn, retrying on transient subprocess failures.

        Retries on :exc:`~quickie.errors.SubprocessExitCodeError` and
        :exc:`~quickie.errors.SubprocessTimeoutError` up to :attr:`retries`
        additional times. All other exceptions propagate immediately.

        :param attempt_fn: A callable that makes a single subprocess attempt.
        :returns: The result of the first successful attempt.
        :raises SubprocessExitCodeError: If all attempts fail with an unexpected
            exit code.
        :raises SubprocessTimeoutError: If all attempts fail due to timeout.
        """
        total_attempts = self.get_retries() + 1
        last_exc: SubprocessExitCodeError | SubprocessTimeoutError | None = None

        for attempt in range(total_attempts):
            if attempt > 0:
                delay = self.get_retry_delay()
                if delay > 0:
                    app.logger.debug(
                        f"Waiting {delay}s before retrying task '{self.name}'."
                    )
                    time.sleep(delay)
                app.logger.warning(
                    f"Retrying task '{self.name}'"
                    f" (attempt {attempt + 1}/{total_attempts})."
                )
            try:
                return attempt_fn()
            except (SubprocessExitCodeError, SubprocessTimeoutError) as e:
                last_exc = e
                if attempt < total_attempts - 1:
                    app.logger.warning(
                        f"Task '{self.name}' attempt {attempt + 1}/{total_attempts}"
                        f" failed: {e}"
                    )

        assert last_exc is not None
        raise last_exc

    def _tee_popen(
        self,
        cmd: list[str] | str,
        *,
        shell: bool = False,
        executable: str | None = None,
        wd: str,
        env: typing.Mapping[str, str],
        timeout: float | None,
    ) -> subprocess.CompletedProcess[bytes]:
        """Run cmd via Popen, streaming to the terminal while capturing output.

        :returns: A :class:`subprocess.CompletedProcess` with populated ``.stdout``
            and ``.stderr`` bytes.
        :raises SubprocessTimeoutError: If the process exceeds *timeout* seconds.
        """
        stdout_chunks: list[bytes] = []
        stderr_chunks: list[bytes] = []

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=shell,
            executable=executable,
            cwd=wd,
            env=env,
        )

        def _drain(pipe: typing.IO[bytes], chunks: list[bytes], dest) -> None:
            for chunk in iter(lambda: pipe.read1(), b""):  # type: ignore[attr-defined]
                chunks.append(chunk)
                dest.write(chunk)
                dest.flush()

        stdout_thread = threading.Thread(
            target=_drain, args=(process.stdout, stdout_chunks, sys.stdout.buffer)
        )
        stderr_thread = threading.Thread(
            target=_drain, args=(process.stderr, stderr_chunks, sys.stderr.buffer)
        )
        stdout_thread.start()
        stderr_thread.start()

        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout_thread.join()
            stderr_thread.join()
            assert timeout is not None
            cmd_str = shlex.join(cmd) if isinstance(cmd, list) else cmd
            raise SubprocessTimeoutError(
                task_name=self.name,
                command=cmd_str,
                timeout=timeout,
            )

        stdout_thread.join()
        stderr_thread.join()

        return subprocess.CompletedProcess(
            args=cmd,
            returncode=process.returncode,
            stdout=b"".join(stdout_chunks),
            stderr=b"".join(stderr_chunks),
        )


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
    def run(self, *args, **kwargs) -> subprocess.CompletedProcess[bytes]:
        cmd = self.get_cmd(*args, **kwargs)
        cmd = self.split_cmd_args(cmd)

        if len(cmd) == 0:
            raise ValueError("No program to run")
        elif len(cmd) == 1:
            program = cmd[0]
            cmd_args = []
        else:
            program, *cmd_args = cmd
        wd = self.get_wd(*args, **kwargs)
        env = self.get_env(*args, **kwargs)
        return self._run_program(program, cmd_args=cmd_args, wd=wd, env=env)

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
        self.log_task_execution_details(program, cmd_args)
        program = self._resolve_program_fallback(program, env) or program
        cmd = [program, *cmd_args]
        expected_exit_codes = self.get_expected_exit_codes()
        timeout = self.get_timeout()
        output_mode = self.output_mode

        def attempt():
            if output_mode is OutputMode.TEE:
                result = self._tee_popen(cmd, wd=wd, env=env, timeout=timeout)
            else:
                try:
                    result = subprocess.run(
                        cmd,
                        check=False,
                        cwd=wd,
                        env=env,
                        timeout=timeout,
                        capture_output=(output_mode is OutputMode.CAPTURE),
                    )
                except subprocess.TimeoutExpired:
                    assert timeout is not None
                    raise SubprocessTimeoutError(
                        task_name=self.name,
                        command=shlex.join(cmd),
                        timeout=timeout,
                    )
            self.validate_exit_code(
                return_code=result.returncode,
                command=shlex.join(cmd),
                expected_exit_codes=expected_exit_codes,
            )
            return result

        return self._execute_with_retry(attempt)

    def _resolve_program_fallback(
        self,
        program: str,
        env: typing.Mapping[str, str],
    ) -> str | None:
        """Resolve fallback executable for missing commands.

        Currently only supports ``python`` to improve compatibility on systems
        where only ``python3`` is available in PATH.
        """
        if program != "python":
            return None

        if os.path.exists(sys.executable):
            return sys.executable

        env_path = env.get("PATH")
        if python3 := shutil.which("python3", path=env_path):
            return python3
        return shutil.which("python3") if env_path is not None else None


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
    def run(self, *args, **kwargs) -> subprocess.CompletedProcess[bytes]:
        script = self.get_script(*args, **kwargs)
        wd = self.get_wd(*args, **kwargs)
        env = self.get_env(*args, **kwargs)
        return self._run_script(script, wd=wd, env=env)

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
        self.log_task_execution_details(script)
        expected_exit_codes = self.get_expected_exit_codes()
        timeout = self.get_timeout()
        output_mode = self.output_mode
        executable = self.executable

        def attempt():
            if output_mode is OutputMode.TEE:
                result = self._tee_popen(
                    script,
                    shell=True,
                    executable=executable,
                    wd=wd,
                    env=env,
                    timeout=timeout,
                )
            else:
                try:
                    result = subprocess.run(
                        script,
                        shell=True,
                        check=False,
                        cwd=wd,
                        env=env,
                        executable=executable,
                        timeout=timeout,
                        capture_output=(output_mode is OutputMode.CAPTURE),
                    )
                except subprocess.TimeoutExpired:
                    assert timeout is not None
                    raise SubprocessTimeoutError(
                        task_name=self.name,
                        command=script,
                        timeout=timeout,
                    )
            self.validate_exit_code(
                return_code=result.returncode,
                command=script,
                expected_exit_codes=expected_exit_codes,
            )
            return result

        return self._execute_with_retry(attempt)


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
    def run(self, *args, **kwargs) -> list[typing.Any]:
        """Run each sub-task in definition order and return their results.

        :returns: A list of each sub-task's return value, in definition order.
        """
        return [self._run_task(task) for task in self.get_tasks(*args, **kwargs)]


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
    def run(self, *args, **kwargs) -> list[typing.Any]:
        """Run each sub-task concurrently and return their results in definition order.

        All sub-tasks are submitted to a thread pool simultaneously.  Every
        task is allowed to run to completion regardless of failures in sibling
        tasks.  If one or more tasks raise, all their exceptions are collected
        and re-raised together as an :exc:`ExceptionGroup` after the pool
        shuts down.

        :returns: A list of each sub-task's return value, in definition order
            (not completion order).
        :raises ExceptionGroup: If one or more sub-tasks raised an exception.
        """
        tasks = list(self.get_tasks(*args, **kwargs))
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.get_max_workers(),
            thread_name_prefix=f"quickie-parallel-task.{self.name}",
        ) as executor:
            futures = [executor.submit(self._run_task, task) for task in tasks]
        # All futures are settled once the pool shuts down (wait=True by default).
        # Collect every exception so none are silently dropped.
        exceptions: list[Exception] = []
        for f in futures:
            exc = f.exception()
            if isinstance(exc, Exception):
                exceptions.append(exc)
            elif exc is not None:
                raise exc  # BaseException (e.g. KeyboardInterrupt)
        if exceptions:
            raise ExceptionGroup("thread group tasks failed", exceptions)
        return [f.result() for f in futures]
