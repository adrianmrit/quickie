"""Task context."""

from collections import ChainMap
import os
from pathlib import Path
import typing


class Context:
    """The context for a task."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        wd: str | Path,
        env: typing.Mapping,
        inherit_env: bool = True,
    ):
        """Initialize the context.

        :param wd: The working directory.
        :param env: The environment variables.
        :param inherit_env: Whether to inherit the environment variables from the parent
            process.
        """
        self.wd = Path(wd)
        # By using ChainMap we can avoid copying the environment variables
        # dictionary every we copy the context or create a new one, but
        # still prevent modifying the original environment variables.
        if env:
            if isinstance(env, ChainMap):
                self._env = ChainMap(*env.maps)
            else:
                self._env = ChainMap({}, typing.cast(dict, env))
        else:
            self._env = ChainMap({})

        if inherit_env:
            self._env.maps.append(os.environ)

    @property
    def env(self):
        """Environment variables."""
        return self._env

    @classmethod
    def default(cls):
        """Returns the default context."""
        # Context should be cheap to create, so we don't need to cache it
        return Context(
            wd=os.getcwd(),
            env={},
        )

    def copy(self):
        """Copy the context."""
        return Context(
            wd=self.wd,
            env=self.env,
            inherit_env=False,
        )
