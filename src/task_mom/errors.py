"""Errors for task-mom."""


class MomError(Exception):
    """Base class for task-mom errors."""

    def __init__(self, message, *, exit_code):
        """Initialize the error."""
        super().__init__(message)
        self.exit_code = exit_code


class TaskNotFoundError(MomError):
    """Raised when a task is not found."""

    def __init__(self, task_name):
        """Initialize the error."""
        super().__init__(f"Task '{task_name}' not found", exit_code=1)


class TasksModuleNotFoundError(MomError):
    """Raised when a module is not found."""

    def __init__(self, module_name):
        """Initialize the error."""
        super().__init__(f"Tasks module {module_name} not found", exit_code=2)
