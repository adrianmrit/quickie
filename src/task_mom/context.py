"""Task context."""

import os
import sys
import typing

from frozendict import frozendict


class Context:
    """The context for a task."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        program_name: str | None = None,
        cwd: str | None = None,
        env: typing.Mapping | None = None,
        stdin=None,
        stdout=None,
        stderr=None
    ):
        """Initialize the context."""
        if program_name is None:
            program_name = os.path.basename(sys.argv[0])

        if cwd is None:
            cwd = os.getcwd()
        if env is None:
            env = frozendict(os.environ)

        if stdin is None:
            stdin = sys.stdin
        if stdout is None:
            stdout = sys.stdout
        if stderr is None:
            stderr = sys.stderr

        self.program_name = program_name
        self.cwd = cwd
        self.env = frozendict(env)
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr

    def copy(self):
        """Copy the context."""
        return Context(
            program_name=self.program_name,
            cwd=self.cwd,
            env=self.env,
            stdin=self.stdin,
            stdout=self.stdout,
            stderr=self.stderr,
        )


class GlobalContext:
    """Singleton global context."""

    _instance: Context

    def __new__(cls):
        """Return the global context."""
        return cls.get()

    @classmethod
    def get(cls) -> Context:
        """Returns a pointer to the global context."""
        if not hasattr(cls, "_instance"):
            cls._instance = Context()
        return cls._instance
