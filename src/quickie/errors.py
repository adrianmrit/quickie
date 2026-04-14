"""Errors for quickie."""

import typing


class QuickieError(Exception):
    """Base class for quickie errors."""

    def __init__(self, message, *, exit_code):
        """Initialize the error.

        :param message: The error message.
        :param exit_code: The exit code
        """
        super().__init__(message)
        self.exit_code = exit_code


class TaskNotFoundError(QuickieError):
    """Raised when a task is not found."""

    def __init__(self, task_name):
        """Initialize the error.

        :param task_name: The name of the task that was not found.
        """
        super().__init__(f"Task '{task_name}' not found", exit_code=1)


class TasksModuleNotFoundError(QuickieError):
    """Raised when a module is not found."""

    def __init__(self, module_name):
        """Initialize the error.

        :param module_name: The name of the module that was not found.
        """
        super().__init__(f"Tasks module {module_name} not found", exit_code=2)


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
