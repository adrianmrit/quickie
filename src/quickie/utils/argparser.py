"""Quickie argument parser utilities.

This module provides a wrapper around the argparse module to simplify
the creation of command line arguments for quickie tasks.
"""

from argparse import Action
from pathlib import Path
import typing


class _ArgparseOptionKwargs(typing.TypedDict, total=False):
    action: str | type[Action]
    nargs: int | str | None
    const: typing.Any
    default: typing.Any
    type: typing.Callable | None
    choices: typing.Iterable | None
    required: bool
    help: str | None
    metavar: str | tuple[str, ...]
    dest: str | None
    version: str


def _get_default_completer(action: Action):
    """Get the completer for the action.

    :param action: The action to get the completer for.
    :return: The completer for the action.
    """
    from argcomplete.completers import FilesCompleter

    if action.choices is not None:
        return None

    if action.type in (None, str, Path):
        return FilesCompleter()

    return None


class Arg:
    """A wrapper for argparse arguments."""

    def __init__(
        self,
        *name_or_flags: str,
        completer: typing.Callable | None = None,
        **kwargs: typing.Unpack[_ArgparseOptionKwargs],
    ):
        """Initialize the argument.

        :param name_or_flags: The name or flags of the argument.
        :param completer: The completer for the argument.
        :param kwargs: The kwargs for the argument.
        """
        self.name_or_flags = name_or_flags
        self.completer = completer
        self.kwargs = kwargs

    def add(self, parser: typing.Any):
        """Setup the argument.

        :param parser: The parser to setup the argument for.
        :return: The action for the argument.
        """
        action = parser.add_argument(*self.name_or_flags, **self.kwargs)
        self.set_completer(action)
        return action

    def set_completer(self, action):
        """Setup the completer for the argument.

        :param action: The action to setup the completer for.
        """
        if self.completer is None:
            completer = _get_default_completer(action)
        else:
            completer = self.completer
        if completer is not None:
            action.completer = completer
