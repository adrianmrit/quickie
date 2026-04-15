"""Errors for quickie."""

import difflib
import typing


class QuickieError(Exception):
    """Base class for quickie errors.

    :cvar exit_code: The default exit code used when this error causes the
        process to exit. Subclasses override this with a class-level attribute.
    """

    exit_code: int = 1

    def __init__(self, message, *, exit_code: int | None = None):
        """Initialize the error.

        :param message: The error message.
        :param exit_code: Override the exit code for this instance. When
            omitted the class-level :attr:`exit_code` is used.
        """
        super().__init__(message)
        if exit_code is not None:
            self.exit_code = exit_code


class TaskNotFoundError(QuickieError):
    """Raised when a task is not found.

    :cvar exit_code: ``127`` — mirrors the POSIX shell convention for
        "command not found".
    """

    exit_code = 127

    def __init__(
        self,
        task_name: str,
        *,
        candidates: typing.Sequence[str] | None = None,
    ):
        """Initialize the error.

        :param task_name: The name of the task that was not found.
        :param candidates: All registered task names, used to suggest close
            matches.  When omitted no suggestion is shown.
        """
        msg = f"Task '{task_name}' not found"
        if candidates:
            close = difflib.get_close_matches(task_name, candidates, n=3, cutoff=0.6)
            if close:
                msg += ". Did you mean: " + ", ".join(f"'{m}'" for m in close) + "?"
        super().__init__(msg)


class CircularDependencyError(QuickieError):
    """Raised when a circular reference is detected while loading namespaces."""

    def __init__(self, namespace_path: str):
        """Initialize the error.

        :param namespace_path: The namespace path where the cycle was detected.
            Pass an empty string to indicate the root namespace.
        """
        location = (
            f"namespace '{namespace_path}'" if namespace_path else "the root namespace"
        )
        super().__init__(
            f"Circular reference detected when loading tasks for {location}"
        )


class TasksModuleNotFoundError(QuickieError):
    """Raised when a tasks module cannot be imported.

    :cvar exit_code: ``78`` — mirrors ``EX_CONFIG`` from :manpage:`sysexits(3)`,
        indicating a configuration or environment problem.
    """

    exit_code = 78

    def __init__(self, module_name):
        """Initialize the error.

        :param module_name: The name of the module that was not found.
        """
        super().__init__(f"Tasks module {module_name} not found")


class SubprocessExitCodeError(QuickieError):
    """Raised when a subprocess task exits with an unexpected code."""

    def __init__(
        self,
        *,
        task_name: str,
        return_code: int,
        command: str,
        expected_exit_codes: typing.Iterable[int],
    ):
        """Initialize the error.

        :param task_name: The task that executed the subprocess.
        :param return_code: The actual subprocess return code.
        :param command: The command or script that was executed.
        :param expected_exit_codes: Accepted exit codes for the task.
        """
        expected = ", ".join(str(code) for code in expected_exit_codes)
        super().__init__(
            (
                f"Task '{task_name}' failed with exit code {return_code}. "
                f"Expected one of: {expected}. Command: {command}"
            ),
            exit_code=return_code,
        )
        self.task_name = task_name
        self.return_code = return_code
        self.command = command
        self.expected_exit_codes = expected_exit_codes


class SubprocessTimeoutError(QuickieError):
    """Raised when a subprocess task exceeds its configured timeout.

    :cvar exit_code: ``124`` — follows the convention used by :manpage:`timeout(1)`.
    """

    exit_code = 124

    def __init__(self, *, task_name: str, command: str, timeout: float):
        """Initialize the error.

        :param task_name: The task that executed the subprocess.
        :param command: The command or script that timed out.
        :param timeout: The timeout value in seconds.
        """
        super().__init__(
            (f"Task '{task_name}' timed out after {timeout}s." f" Command: {command}"),
        )
        self.task_name = task_name
        self.command = command
        self.timeout = timeout


class Stop(Exception):
    """Raised when execution should stop.

    Stop exceptions are caught by the CLI such that the process exits
    cleanly. So this is useful for gracefully stopping execution.
    """

    def __init__(self, message: str | None = None, exit_code: int = 0):
        """Initialize the error.

        :param message: An optional message to display.
        :param exit_code: The exit code if applicable.
        """
        self.message = message
        self.exit_code = exit_code
        super().__init__(message)


class Skip(Exception):
    """Raised when a task should be skipped."""

    def __init__(self, message: str | None = None):
        """Initialize the error.

        :param message: An optional message to display.
        """
        self.message = message
        super().__init__(message)
