"""Task context."""

import typing

from frozendict import frozendict
from rich.console import Console

from quickie.namespace import Namespace


class Context:
    """The context for a task."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        program_name,
        cwd: str,
        env: typing.Mapping,
        console: Console,
        namespace: Namespace,
    ):
        """Initialize the context."""
        self.program_name = program_name
        self.cwd = cwd
        self.env = frozendict(env)
        self.console = console
        self.namespace = namespace

    def copy(self):
        """Copy the context."""
        return Context(
            program_name=self.program_name,
            cwd=self.cwd,
            env=self.env,
            console=self.console,
            namespace=self.namespace,
        )
