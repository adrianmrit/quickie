"""The ``:autocomplete`` command — shell completion setup."""

from __future__ import annotations

import os
import sys
import typing
from argparse import ArgumentParser
from argcomplete.completers import ChoicesCompleter

from quickie import app
from quickie.commands.base import CliCommand


class AutocompleteCommand(CliCommand):
    """Print shell completion setup instructions."""

    @typing.override
    def configure_parser(self, parser: ArgumentParser) -> None:
        action = parser.add_argument(
            "shell",
            choices=["bash", "zsh"],
            metavar="SHELL",
            help="Shell to configure",
        )
        action.completer = ChoicesCompleter(["bash", "zsh"])  # type: ignore

    @typing.override
    def execute(self, namespace: object) -> None:
        ns = typing.cast("_AutocompleteNamespace", namespace)
        if ns.shell == "bash":
            _suggest_bash()
        elif ns.shell == "zsh":
            _suggest_zsh()


def _suggest_bash() -> None:
    """Suggest autocompletion for bash."""
    program = os.path.basename(sys.argv[0])
    app.console.print("Add the following to ~/.bashrc or ~/.bash_profile:")
    app.console.print(
        f'eval "$(register-python-argcomplete {program})"',
        style="bold green",
    )


def _suggest_zsh() -> None:
    """Suggest autocompletion for zsh."""
    program = os.path.basename(sys.argv[0])
    app.console.print("Add the following to ~/.zshrc:")
    app.console.print(
        f'eval "$(register-python-argcomplete {program})"',
        style="bold green",
    )


class _AutocompleteNamespace:
    """Minimal type hint for the ``:autocomplete`` namespace."""

    shell: str
