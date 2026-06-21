"""Task context."""

from collections import ChainMap
import os
from pathlib import Path
import typing

from dotenv import dotenv_values


def load_env_file(path: str | Path) -> dict[str, str]:
    """Load environment variables from a ``.env`` file and return them as a dict.

    Variables declared without a value (``VAR`` with no ``=``) are omitted;
    variables with an empty value (``VAR=``) are kept as empty strings.

    This can be used standalone to inspect or forward values:

    .. code-block:: python

        # _qk/__init__.py — apply .env globally before tasks run
        from quickie import app, Context
        from quickie.context import load_env_file
        from pathlib import Path

        _env_path = Path(__file__).parent.parent / ".env"
        app.set_context(Context.from_env_file(_env_path))

    Or independently, e.g. inside a regular task:

    .. code-block:: python

        from quickie import task
        from quickie.context import load_env_file

        @task
        def show_db_url():
            env = load_env_file(".env")
            print(env.get("DATABASE_URL"))

    :param path: Path to the ``.env`` file.  Resolve the path before calling
        when you need base-directory semantics, e.g.
        ``load_env_file(base_dir / ".env")``.

    :returns: A :class:`dict` mapping variable names to string values.
    """
    return {k: v for k, v in dotenv_values(path).items() if v is not None}


def resolve_wd(wd: str | Path | None) -> str:
    """Resolve a working directory value to an absolute path.

    Follows the same resolution rules as task working directories:

    - ``None`` — uses :attr:`app.context.wd <quickie.config.App.context>`
    - ``"."`` — uses the parent of the tasks module directory
    - ``"./some/path"`` — resolved relative to the parent of the tasks module
      directory
    - Other relative path — joined with ``app.context.wd``
    - Absolute path — used as-is

    :param wd: The working directory value to resolve.
    :returns: An absolute path string.
    """
    from quickie import app  # noqa: PLC0415

    if wd is None:
        path = app.context.wd
    elif wd == ".":
        path = app.tasks_path.parent
    elif isinstance(wd, str) and wd.startswith("./"):
        path = os.path.join(app.tasks_path.parent, wd)
    elif not os.path.isabs(wd):
        path = os.path.join(app.context.wd, wd)
    else:
        path = wd
    return os.path.abspath(path)


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

    @classmethod
    def from_env_file(
        cls,
        path: str | Path,
        *,
        wd: str | Path | None = None,
        base_dir: str | Path | None = None,
        env: typing.Mapping[str, str] | None = None,
        inherit_env: bool = True,
    ) -> "Context":
        """Create a :class:`Context` with env variables loaded from a ``.env`` file.

        Explicit *env* values take precedence over values loaded from the file.

        .. code-block:: python

            from quickie.context import Context
            from quickie import app

            app.set_context(Context.from_env_file(".env", base_dir="/project"))

        :param path: Path to the ``.env`` file. Resolved relative to *base_dir*
            when given and the path is not absolute.
        :param wd: The working directory for the new context.  Defaults to the
            current working directory.
        :param base_dir: Base directory used to resolve a relative *path*.
        :param env: Additional explicit environment variables that override
            values loaded from the file.
        :param inherit_env: Whether to inherit OS environment variables.

        :returns: A new :class:`Context` containing the merged environment.
        """
        file_env: dict[str, str] = load_env_file(
            os.path.join(base_dir, path)
            if base_dir is not None and not os.path.isabs(path)
            else path
        )
        if env:
            # Explicit env overrides file-loaded values
            merged: typing.Mapping[str, str] = ChainMap(dict(env), file_env)
        else:
            merged = file_env
        return cls(
            wd=wd if wd is not None else os.getcwd(),
            env=merged,
            inherit_env=inherit_env,
        )

    def copy(self):
        """Copy the context."""
        return Context(
            wd=self.wd,
            env=self.env,
            inherit_env=False,
        )
