"""Abstract base for built-in CLI commands."""

from __future__ import annotations

from argparse import ArgumentParser

import argcomplete


class CliCommand:
    """Interface for a built-in CLI subcommand.

    Subclasses override the instance methods below.
    The base class is not an ABC because all the real protocol is
    convention — there are no abstract methods to enforce at import time.
    """

    def configure_parser(self, parser: ArgumentParser) -> None:
        """Add arguments and metadata to *parser*, an argparse subparser."""
        raise NotImplementedError

    def execute(self, namespace: object) -> None:
        """Execute this command with the given parsed *namespace*."""
        raise NotImplementedError

    def autocomplete(self, parser: ArgumentParser, args: list[str]) -> None:
        """Complete arguments for this command."""
        del args
        argcomplete.autocomplete(parser)
