"""Base class for auto-completing python modules."""

import argparse
import traceback
import typing

import argcomplete


class BaseCompleter(argcomplete.completers.BaseCompleter):
    """Base class for completers."""

    def complete(
        self,
        *,
        prefix: str,
        action: argparse.Action,
        parser: argparse.ArgumentParser,
        parsed_args: argparse.Namespace,
    ) -> list[str] | dict[str, str]:
        """Complete the prefix.

        :param prefix: The prefix to complete.
        :param action: The action to complete.
        :param parser: The parser to complete.
        :param parsed_args: The parsed arguments.
        """
        raise NotImplementedError

    @typing.override
    def __call__(
        self,
        prefix: str,
        action: argparse.Action,
        parser: argparse.ArgumentParser,
        parsed_args: argparse.Namespace,
    ) -> list[str] | dict[str, str]:
        """Call the completer.

        Do not override this method, as it automatically handles exceptions.
        Override the :meth:`complete` method instead.
        """
        try:
            return self.complete(
                prefix=prefix, action=action, parser=parser, parsed_args=parsed_args
            )
        except Exception:
            # Include stack trace in the warning
            argcomplete.io.warn(
                f"Autocompletion by {self.__class__.__name__} failed with error:",
                traceback.format_exc(),
            )
            return []
