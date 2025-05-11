"""Settings for quickie."""

from functools import cached_property
import logging
import logging.handlers
import os
from pathlib import Path
import sys

from frozendict import frozendict

from quickie.context import Context
from quickie.utils import imports
from quickie.utils.console import QkConsole
from rich.theme import Theme
from rich.text import Text
from rich.logging import RichHandler
from quickie._namespace import RootNamespace

HOME_PATH_ENV = "QK_HOME_PATH"
TMP_RELATIVE_PATH_ENV = "QK_TMP_RELATIVE_PATH"
LOG_LEVEL_ENV = "QK_LOG_LEVEL"
LOG_FILE_ENV = "QK_LOG_FILE"


class _PlainFormatter(logging.Formatter):
    """Removes markup from the log message."""

    def format(self, record):
        # Remove markup from the message
        record.msg = Text.from_markup(record.msg).plain
        return super().format(record)


class App:
    """Represents the application configuration and other utilities available globally.

    This class is a singleton, meaning that only one instance of it can exist at a time.
    Calling the constructor will always return the same instance.
    """

    console_style: frozendict
    log_level: int
    log_file: str | Path | None

    console_style = frozendict(
        {
            "info": os.environ.get("QUICKIE_RUNNER_INFO_STYLE", "cyan"),
            "warning": os.environ.get("QUICKIE_RUNNER_WARNING_STYLE", "yellow"),
            "error": os.environ.get("QUICKIE_RUNNER_ERROR_STYLE", "red"),
            "success": os.environ.get("QUICKIE_RUNNER_SUCCESS_STYLE", "green"),
        }
    )

    def __new__(cls):
        """Ensure that only one instance of the App class is created."""
        if not hasattr(cls, "_instance"):
            cls._instance = super().__new__(cls)
            cls._instance.__init__()
        return cls._instance

    def __init__(self):
        """Initialize the application configuration."""
        self.program_name = os.path.basename(sys.argv[0])

        self.logger = logging.getLogger("quickie")
        self.logger.handlers.clear()
        self.logger.addHandler(
            RichHandler(
                rich_tracebacks=True,
                markup=True,
                console=self.error_console,
                show_path=False,
                show_time=False,
            )
        )
        self.context = Context.default()

    @cached_property
    def console(self):
        """Console for standard output."""
        return QkConsole(theme=Theme(self.console_style))

    @cached_property
    def error_console(self):
        """Console for error messages."""
        # console that writes to stderr
        return QkConsole(theme=Theme(self.console_style), stderr=True)

    @property
    def tasks(self) -> RootNamespace:
        """The root namespace for the application."""
        if not hasattr(self, "_tasks"):
            raise ValueError(
                "Tasks not loaded. Call load_tasks() before accessing tasks."
            )
        return self._tasks

    @property
    def home_path(self) -> Path:
        """The path to the global quickie directory. Usually `~._qkg`."""
        if not hasattr(self, "_home_path"):
            self.set_home_path(
                Path(os.environ.get(HOME_PATH_ENV, str(Path.home() / "_qkg")))
            )
        return self._home_path

    @property
    def project_path(self) -> Path:
        """The path to the tasks module."""
        if not hasattr(self, "_project_path"):
            # Traversing should not occur unless project_path is not set and is accessed
            self.set_project_path(
                self._resolve_module_path(module_name="_qk", traverse=True)
            )
        return self._project_path

    @property
    def use_global(self) -> bool:
        """Whether to use the global quickie directory."""
        if not hasattr(self, "_use_global"):
            self.set_use_global(False)
        return self._use_global

    @property
    def tasks_path(self) -> Path:
        """The path to the tasks module."""
        if self.use_global:
            return self.home_path
        return self.project_path

    @property
    def tmp_relative_path(self) -> Path:
        """The path to the temporary directory."""
        if not hasattr(self, "_tmp_relative_path"):
            self.set_tmp_relative_path(
                Path(os.environ.get(TMP_RELATIVE_PATH_ENV, "tmp"))
            )
        return self._tmp_relative_path

    @property
    def tmp_path(self) -> Path:
        """The path to the temporary directory."""
        return self.tasks_path / self.tmp_relative_path

    def set_context(self, context: Context):
        """Set the context for the application.

        :param context: The context to set.
        """
        self.context = context
        self.logger.debug(f"Context set to: {self.context}")

    def set_home_path(self, value: str | Path):
        """Set the home path for the application.

        :param value: The path to the home directory.
        """
        if isinstance(value, str):
            value = Path(value)
        self._home_path = value
        self.logger.debug(f"Home path set to: {self._home_path}")

    def set_project_path(self, value: str | Path):
        """Set the project path for the application.

        :param value: The path to the project directory.
        """
        if isinstance(value, str):
            value = Path(value)
        self._project_path = self._resolve_module_path(
            module_name=value, traverse=False
        )
        self.logger.debug(f"Project path set to: {self._project_path}")

    def set_use_global(self, value: bool):
        """Set whether to use the global quickie directory.

        :param value: Whether to use the global directory.
        """
        self._use_global = value
        self.logger.debug(f"Use global set to: {self._use_global}")

    def set_tmp_relative_path(self, value: str | Path):
        """Set the temporary relative path for the application.

        :param value: The path to the temporary directory.
        """
        if isinstance(value, str):
            value = Path(value)
        self._tmp_relative_path = value
        self.logger.debug(f"Temporary relative path set to: {self._tmp_relative_path}")

    def set_verbosity(self, verbosity: int):
        """Configure the logging level.

        :param verbosity: The verbosity level. -1 for quiet, 0 for normal,
            1 for verbose, 2 for very verbose.
        """
        self.verbosity = min(verbosity, 2)

        if verbosity == 0:
            # Verbosity not given, check for environment variable
            env_loglevel = os.getenv(LOG_LEVEL_ENV, "WARNING").upper()
            log_level = getattr(logging, env_loglevel, None)
            if log_level is None:
                raise ValueError(
                    f"Invalid log level set in environment variable: {env_loglevel}."
                )
            self.log_level = log_level
        else:
            base_loglevel = logging.WARNING
            # Python log levels go from 10 (DEBUG) to 50 (CRITICAL),
            # Decrease the log level by 10 for each verbosity level,
            # starting from WARNING (30). Thus by default we show warnings
            # and above, with `-v` we show info and above, and with `-vv`
            # we show debug. If `-q` is given, we show critical only.
            self.log_level = base_loglevel - (self.verbosity * 10)

        self.logger.setLevel(self.log_level)
        # set level for the root logger
        logging.getLogger().setLevel(self.log_level)
        self.logger.debug(f"Log level set to: {self.log_level}")

    def set_log_file(self, log_file: str | Path | None):
        """Set the log file for the application.

        :param log_file: The path to the log file. If None, will attempt to
            use the environment variable `QK_LOG_FILE`, otherwise will not
            log to a file.
        """
        if isinstance(log_file, str):
            log_file = Path(log_file)

        self.log_file = os.getenv(LOG_FILE_ENV, log_file)
        if self.log_file:
            file_handler = logging.handlers.RotatingFileHandler(
                self.log_file, maxBytes=5 * 1024 * 1024, backupCount=5
            )
            file_handler.setFormatter(
                _PlainFormatter("%(asctime)s:%(levelname)s:%(name)s:%(message)s")
            )
            self.logger.addHandler(file_handler)
            self.logger.debug(f"Log file set to: {self.log_file}")
        else:
            self.logger.debug("No log file set; logging to console only.")

    def configure(self, **kwargs):
        """Configure the application.

        This is a shortcut to setattr the attributes of the class.
        """
        # We don't set absolute paths, to preserve the original value if displaying
        # it to the user. Also assuming that if the value is relative it was intended
        # by the user.
        for key, value in kwargs.items():
            target_fn_name = f"set_{key}"
            if hasattr(self, target_fn_name):
                target_fn = getattr(self, target_fn_name)
                if callable(target_fn):
                    target_fn(value)
                    continue
            raise ValueError(f"Invalid configuration key: {key}.")

    def _resolve_module_path(self, module_name: str | Path, traverse: bool) -> Path:
        """Resolves the right path for the module.

        :param module_name: The name of the module.
        :param traverse: Whether to traverse the parent directories
            to find the module. Defaults to True.

        :return: The resolved path.
        """
        from quickie.errors import TasksModuleNotFoundError

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

    def load_tasks(self):
        """Load tasks from the tasks module."""
        root = Path.cwd()
        module = imports.import_from_path(root / self.tasks_path)
        self._tasks = RootNamespace()
        self._tasks.load(module)


app = App()
"""Default configuration."""

console = app.console
"""Default console."""

error_console = app.error_console
"""Default error console."""

logger = app.logger
"""Default logger."""

context = app.context
"""Default context."""
