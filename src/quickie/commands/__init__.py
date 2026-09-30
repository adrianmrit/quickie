"""Built-in CLI commands for quickie.

Each command is an instance of a ``CliCommand`` subclass:

* ``configure_parser(parser)`` — add subparser arguments
* ``autocomplete(parser, args)`` — complete command arguments
* ``execute(namespace)`` — run the command

Add new commands by creating a module in this package, implementing a
``CliCommand`` subclass, creating an instance, and adding it to ``COMMANDS``.
"""

from __future__ import annotations

from .base import CliCommand
from .list_ import ListCommand
from .watch import WatchCommand
from .init import InitCommand
from .autocomplete import AutocompleteCommand
from .run import RunCommand

COMMANDS: dict[str, CliCommand] = {
    ":list": ListCommand(),
    ":watch": WatchCommand(),
    ":init": InitCommand(),
    ":autocomplete": AutocompleteCommand(),
    ":run": RunCommand(),
}

__all__ = ["COMMANDS", "CliCommand"]
