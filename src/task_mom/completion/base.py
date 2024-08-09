"""Base class for auto-completing python modules."""

import argparse
import os
import traceback
import typing

import argcomplete


class BaseCompleter(argcomplete.completers.BaseCompleter):
    """For auto-completing python modules."""

    def complete(
        self,
        *,
        prefix: str,
        action: argparse.Action,
        parser: argparse.ArgumentParser,
        parsed_args: argparse.Namespace,
    ) -> list[str] | dict[str, str]:
        """Complete the prefix."""
        pass

    @typing.override
    def __call__(
        self,
        prefix: str,
        action: argparse.Action,
        parser: argparse.ArgumentParser,
        parsed_args: argparse.Namespace,
    ):
        """Call the completer."""
        try:
            return self.complete(
                prefix=prefix, action=action, parser=parser, parsed_args=parsed_args
            )
        except Exception:
            # Include stack trace in the warning
            argcomplete.warn(
                f"Autocompletion by {self.__class__.__name__} failed with error:",
                traceback.format_exc(),
            )


class PathCompleter(BaseCompleter):
    """For auto-completing file paths."""

    def get_pre_filtered_paths(self, target_dir: str) -> typing.Iterator[str]:
        """Get path names in the target directory."""
        try:
            return os.listdir(target_dir or ".")
        except Exception:
            return []

    def get_paths(self, prefix: str) -> typing.Generator[str, None, None]:
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
        return list(self.get_paths(prefix))
