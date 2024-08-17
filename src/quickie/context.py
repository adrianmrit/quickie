"""Task context."""

import typing

from frozendict import frozendict
from rich.console import Console

from quickie._namespace import NamespaceABC
from quickie.config import CliConfig


class Context:
    """The context for a task."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        program_name,
        cwd: str,
        env: typing.Mapping,
        console: Console,
        namespace: NamespaceABC,
        config: CliConfig,
    ):
        """Initialize the context.

        :param program_name: The name of the program. Usually `qck` or `qckg`.
        :param cwd: The current working directory.
        :param env: The environment variables.
        :param console: A Console instance.
        :param namespace: The namespace for the task.
        :param config: The configuration for the CLI.
        """
        self.program_name = program_name
        self.cwd = cwd
        self.env = frozendict(env)
        self.console = console
        self.namespace = namespace
        self.config = config

    def copy(self):
        """Copy the context."""
        return Context(
            program_name=self.program_name,
            cwd=self.cwd,
            env=self.env,
            console=self.console,
            namespace=self.namespace,
            config=self.config,
        )
