"""Task context."""

from collections import ChainMap
import os
import typing


class Context:
    """The context for a task."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        cwd: str,
        env: typing.Mapping,
    ):
        """Initialize the context.

        :param cwd: The current working directory.
        :param env: The environment variables.
        """
        self.cwd = cwd
        self._env = ChainMap(
            # Modifications will be made to this dictionary
            {},
            env,  # type: ignore
            os.environ,
        )

    @property
    def env(self):
        """Environment variables."""
        return self._env

    @classmethod
    def default(cls):
        """Create a context from the environment."""
        return Context(
            cwd=os.getcwd(),
            env={},
        )

    def copy(self):
        """Copy the context."""
        return Context(
            cwd=self.cwd,
            env=self.env.new_child(),
        )
