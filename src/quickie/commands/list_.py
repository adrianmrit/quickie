"""The ``:list`` command — list available tasks."""

from __future__ import annotations

import json
import os
import sys
import typing

from argparse import ArgumentParser, SUPPRESS

import quickie
from quickie import app
from quickie.commands.base import CliCommand


class ListCommand(CliCommand):
    """List available tasks."""

    @typing.override
    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument("--filter", nargs="?", const="", dest="list_filter")
        parser.add_argument(
            "--json", action="store_true", dest="list_json", help=SUPPRESS
        )

    @typing.override
    def execute(self, namespace: object) -> None:
        ns = typing.cast("_ListNamespace", namespace)

        # Handle JSON listing before any Rich/logger output so that stdout
        # contains only the raw JSON (used by qk-mcp to enumerate tasks).
        app.load_tasks()
        if ns.list_json:
            self._list_tasks_json(ns.list_filter)
            return

        self._list_tasks(ns.list_filter)

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _task_list_entries(filter_text: str | None = None) -> list[dict]:
        """Build task metadata grouped by the namespace they invoke from."""
        cwd = os.getcwd()
        grouped: dict[int, tuple[quickie.Task, list[str]]] = {}
        for invocation_name, task in app.tasks.items():
            grouped.setdefault(id(task), (task, []))[1].append(invocation_name)

        entries: list[dict] = []
        for task, invocation_names in grouped.values():
            entry = task.to_info_dict(cwd)
            if task.name in invocation_names:
                entry["name"] = task.name
            else:
                canonical_paths = [
                    name for name in invocation_names if name.endswith(f":{task.name}")
                ]
                entry["name"] = min(
                    canonical_paths or invocation_names,
                    key=lambda name: name.split(":"),
                )
            entry["aliases"] = sorted(
                name for name in invocation_names if name != entry["name"]
            )
            entries.append(entry)

        if filter_text:
            needle = filter_text.casefold()
            entries = [
                entry
                for entry in entries
                if needle in entry["name"].casefold()
                or any(needle in alias.casefold() for alias in entry["aliases"])
            ]
        return sorted(entries, key=lambda entry: entry["name"])

    @staticmethod
    def _list_tasks_json(filter_text: str | None = None) -> None:
        """Output tasks as JSON for machine-readable consumption (e.g. qk-mcp)."""
        result = ListCommand._task_list_entries(filter_text)
        sys.stdout.write(json.dumps(result))
        sys.stdout.write("\n")
        sys.stdout.flush()

    @staticmethod
    def _list_tasks(filter_text: str | None = None) -> None:
        """List the available tasks."""
        import rich.box
        import rich.table
        import rich.text

        table = rich.table.Table(title="Available tasks", box=rich.box.ROUNDED)
        table.show_lines = True
        table.add_column("Task", style="bold yellow", no_wrap=True)
        table.add_column("Aliases", style="bold yellow", no_wrap=True)
        table.add_column("Short Description", style="bold yellow")
        table.add_column("Location")

        for entry in ListCommand._task_list_entries(filter_text):
            rich_task_name = rich.text.Text(entry["name"], style="bold")
            rich_aliases = rich.text.Text("\n".join(entry["aliases"]), style="dim")
            task_location = rich.text.Text(entry["location"] or "", style="dim")
            short_help = rich.text.Text(entry["short_help"], style="green")
            table.add_row(rich_task_name, rich_aliases, short_help, task_location)

        app.console.print(table)


class _ListNamespace:
    """Minimal type hint for the ``:list`` namespace."""

    list_filter: str | None
    list_json: bool
