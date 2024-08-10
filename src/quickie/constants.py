"""Settings for quickie."""

from pathlib import Path

from frozendict import frozendict

HOME_PATH = Path.home() / "Quickie"
SETTINGS_PATH = HOME_PATH / "settings.toml"
TASKS_PATH = Path("__quickie")

DEFAULT_CONSOLE_STYLE = frozendict(
    {
        "info": "cyan",
        "warning": "yellow",
        "error": "bold red",
        "success": "green",
    }
)
