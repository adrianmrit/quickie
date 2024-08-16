"""Settings for quickie."""

import os
from dataclasses import dataclass
from pathlib import Path

from frozendict import frozendict

from quickie.errors import TasksModuleNotFoundError

HOME_PATH_ENV = "QUICKIE_RUNNER_HOME_PATH"
TMP_RELATIVE_PATH_ENV = "QUICKIE_RUNNER_TMP_RELATIVE_PATH"

# TODO: Make configurable via ENV variables or CLI arguments.
# INFO_STYLE_ENV = "QUICKIE_RUNNER_INFO_STYLE"
# WARNING_STYLE_ENV = "QUICKIE_RUNNER_WARNING_STYLE"
# ERROR_STYLE_ENV = "QUICKIE_RUNNER_ERROR_STYLE"
# SUCCESS_STYLE_ENV = "QUICKIE_RUNNER_SUCCESS_STYLE"

CONSOLE_STYLE = frozendict(
    {
        "info": "cyan",
        "warning": "yellow",
        "error": "bold red",
        "success": "green",
    }
)


# Just so that we can mock it in tests, as we don't want to persist the changes.
def _get_and_set_env(name: str, value: str | None, default: str):
    """Resolves the right value for an environment variable,and updates the environment.

    Args:
        name (str): The name of the environment variable.
        value (str): The preferred value to use. I.e. value directly passed to the CLI.
        default (str): The default value to use if value is not given and the
            environment variable is not set.
    """
    if not value:
        value = os.environ.get(name, default)
    os.environ[name] = value
    return value


@dataclass(frozen=True, init=False)
class CliConfig:
    """Settings for quickie."""

    HOME_PATH: Path
    TASKS_MODULE_PATH: str
    TMP_RELATIVE_PATH: str
    TMP_PATH: Path

    def __init__(  # noqa: PLR0913
        self,
        *,
        home_path: str | None = None,
        tasks_module_name: str | None = None,
        tmp_relative_path: str | None = None,
        use_global: bool,
    ):
        """Initialize the configuration."""
        # We don't set absolute paths, to preserve the original value if displaying
        # it to the user. Also assuming that if the value is relative it was intended
        # by the user.
        object.__setattr__(
            self,
            "HOME_PATH",
            Path(
                _get_and_set_env(HOME_PATH_ENV, home_path, str(Path.home() / "Quickie"))
            ),
        )

        # This should not be set through the environment, as it would defeat the purpose
        # of the tasks being shared across different projects. I.e. would need to specify
        # the module every time.
        if use_global and not tasks_module_name:
            object.__setattr__(self, "TASKS_MODULE_PATH", self.HOME_PATH)
        else:
            if tasks_module_name:
                traverse = False
            else:
                traverse = True
                tasks_module_name = "__quickie"
            object.__setattr__(
                self,
                "TASKS_MODULE_PATH",
                self._resolve_module_path(
                    module_name=tasks_module_name, traverse=traverse
                ),
            )

        object.__setattr__(
            self,
            "TMP_RELATIVE_PATH",
            _get_and_set_env(TMP_RELATIVE_PATH_ENV, tmp_relative_path, "tmp"),
        )
        object.__setattr__(
            self, "TMP_PATH", self.TASKS_MODULE_PATH / self.TMP_RELATIVE_PATH
        )

    def _resolve_module_path(self, module_name, traverse: bool) -> Path:
        """Resolves the right path for the module.

        Args:
            module_name: The name of the module.
            traverse: Whether to traverse the parent directories
                to find the module. Defaults to True.
        """
        current = Path.cwd()
        module_path = Path(module_name)
        while True:
            full_path = current / module_path
            if full_path.exists() and full_path.is_dir():
                return full_path

            if not module_path.suffix == ".py":
                full_path = full_path.with_suffix(".py")
                if full_path.exists() and full_path.is_file():
                    return full_path

            if not traverse or current == current.parent:
                break
            current = current.parent
        raise TasksModuleNotFoundError(module_name)

    def get_env(self):
        """Get the environment variables."""
        return {
            HOME_PATH_ENV: str(self.HOME_PATH),
            TMP_RELATIVE_PATH_ENV: str(self.TMP_RELATIVE_PATH),
        }
