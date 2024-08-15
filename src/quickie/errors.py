"""Errors for quickie."""


class QuickieError(Exception):
    """Base class for quickie errors."""

    def __init__(self, message, *, exit_code):
        """Initialize the error."""
        super().__init__(message)
        self.exit_code = exit_code


class TaskNotFoundError(QuickieError):
    """Raised when a task is not found."""

    def __init__(self, task_name):
        """Initialize the error."""
        super().__init__(f"Task '{task_name}' not found", exit_code=1)


class TasksModuleNotFoundError(QuickieError):
    """Raised when a module is not found."""

    def __init__(self, module_name):
        """Initialize the error."""
        super().__init__(f"Tasks module {module_name} not found", exit_code=2)


class Stop(Exception):
    """Raised when execution should stop.

    Stop exceptions are caught by the CLI such that the process exits
    cleanly. So this is useful for gracefully stopping execution.
    """

    def __init__(self, message: str | None = None, exit_code: int = 0):
        """Initialize the error."""
        self.message = message
        self.exit_code = exit_code
        super().__init__(message)
