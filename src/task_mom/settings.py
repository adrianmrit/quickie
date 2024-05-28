"""Settings for task_mom."""

from frozendict import frozendict

DEFAULT_CONSOLE_STYLE = frozendict(
    {
        "info": "cyan",
        "warning": "yellow",
        "error": "bold red",
        "success": "green",
    }
)
