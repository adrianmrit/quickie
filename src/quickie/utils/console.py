"""Console utilities for Quickie."""

import typing as t

import rich.console
from rich.theme import Theme
from rich.prompt import Prompt, Confirm


class QkConsole(rich.console.Console):
    """Extends the rich console to add more utility methods."""

    def __init__(self, *args, **kwargs):
        """Initialize the console."""
        if "theme" not in kwargs:
            from quickie import app

            console_theme = Theme(app.console_style)
            kwargs["theme"] = console_theme
        super().__init__(*args, **kwargs)

    def print_error(self, *args, **kwargs):
        """Print an error message."""
        kwargs.setdefault("style", "error")
        self.print(*args, **kwargs)

    def print_success(self, *args, **kwargs):
        """Print a success message."""
        kwargs.setdefault("style", "success")
        self.print(*args, **kwargs)

    def print_warning(self, *args, **kwargs):
        """Print a warning message."""
        kwargs.setdefault("style", "warning")
        self.print(*args, **kwargs)

    def print_info(self, *args, **kwargs):
        """Print an info message."""
        kwargs.setdefault("style", "info")
        self.print(*args, **kwargs)

    def prompt(  # noqa: PLR0913
        self,
        prompt,
        *,
        password: bool = False,
        choices: list[str] | None = None,
        show_default: bool = True,
        show_choices: bool = True,
        default: t.Any = ...,
    ) -> str:
        """Prompt the user for input.

        :param prompt: The prompt message.
        :param password: Whether to hide the input.
        :param choices: List of choices.
        :param show_default: Whether to show the default value.
        :param show_choices: Whether to show the choices.
        :param default: The default value.

        :return: The user input.
        """
        return Prompt.ask(
            prompt,
            console=self,
            password=password,
            choices=choices,
            show_default=show_default,
            show_choices=show_choices,
            default=default,
        )

    def confirm(self, prompt, default: bool = False) -> bool:
        """Prompt the user for confirmation.

        :param prompt: The prompt message.
        :param default: The default value.

        :return: True if the user confirms, False otherwise.
        """
        return Confirm.ask(prompt, console=self, default=default)
