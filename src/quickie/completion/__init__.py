"""Completers for task arguments.

This module provides completers for task arguments. A completer is a function that
suggests possible values for an argument based on the current input.
"""

import argparse
import os
import typing

from quickie.completion.base import BaseCompleter

__all__ = ["BaseCompleter", "PathCompleter"]


class PathCompleter(BaseCompleter):
    """For auto-completing file paths."""

    def get_pre_filtered_paths(self, target_dir: str) -> typing.Iterable[str]:
        """Get path names in the target directory."""
        try:
            return os.listdir(target_dir or ".")
        except Exception:
            return []

    def _get_paths(self, prefix: str) -> typing.Generator[str, None, None]:
        """Get path names that match the prefix."""
        target_dir = os.path.dirname(prefix)
        names = self.get_pre_filtered_paths(target_dir)
        incomplete_part = os.path.basename(prefix)
        # Iterate on target_dir entries and filter on given predicate
        for name in names:
            if not name.startswith(incomplete_part):
                continue
            candidate = os.path.join(target_dir, name)
            yield candidate + "/" if os.path.isdir(candidate) else candidate

    @typing.override
    def complete(
        self,
        *,
        prefix: str,
        action: argparse.Action,
        parser: argparse.ArgumentParser,
        parsed_args: argparse.Namespace,
    ):
        """Complete the prefix."""
        return list(self._get_paths(prefix))
