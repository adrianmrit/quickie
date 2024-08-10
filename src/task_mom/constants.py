"""Settings for task_mom."""

from pathlib import Path

from frozendict import frozendict

HOME_PATH = Path.home() / "mom"
SETTINGS_PATH = HOME_PATH / "settings.toml"
TASKS_PATH = Path("__mom__")

DEFAULT_CONSOLE_STYLE = frozendict(
    {
        "info": "cyan",
        "warning": "yellow",
        "error": "bold red",
        "success": "green",
    }
)
