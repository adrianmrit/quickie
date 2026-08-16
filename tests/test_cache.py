"""Tests for the task cache."""

from __future__ import annotations

import os
import time


from quickie._cache import (
    TaskCache,
    _detect_completer_type,
    build_cache_entry,
    rebuild_parser,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _StubTask:
    """Minimal task-like object for testing build_cache_entry."""

    def __init__(self, name: str, help_text: str = "", args=None):
        self.name = name
        self._help = help_text
        self._args = args or []
        self._parser = None

    def get_short_help(self):
        return self._help

    @property
    def parser(self):
        if self._parser is None:
            import argparse

            self._parser = argparse.ArgumentParser(prog=self.name)
            for a in self._args:
                if isinstance(a, dict):
                    flags = a.pop("flags")
                    self._parser.add_argument(*flags, **a)
        return self._parser

    @property
    def _actions(self):
        return self.parser._actions

    def _get_args_schema(self):
        import argparse

        schema = []
        for action in self.parser._actions:
            if isinstance(action, argparse._HelpAction):
                continue
            type_name = None
            if action.type is not None:
                type_name = getattr(action.type, "__name__", str(action.type))
            elif not action.option_strings:
                type_name = "str"
            schema.append(
                {
                    "flags": list(action.option_strings) or [action.dest],
                    "dest": action.dest,
                    "type": type_name,
                    "default": action.default
                    if action.default is not argparse.SUPPRESS
                    else None,
                    "required": getattr(action, "required", False),
                    "choices": list(action.choices) if action.choices else None,
                    "help": action.help,
                    "nargs": action.nargs,
                }
            )
        return schema


# ---------------------------------------------------------------------------
# TaskCache.save / load
# ---------------------------------------------------------------------------


class TestTaskCache:
    def test_save_and_load(self, tmp_path):
        tasks = {"build": {"help": "Build it", "args": None}}
        TaskCache.save(tmp_path, tasks, "1.0.0")
        result = TaskCache.load(tmp_path, "1.0.0")
        assert result == tasks

    def test_load_returns_none_when_missing(self, tmp_path):
        assert TaskCache.load(tmp_path, "1.0.0") is None

    def test_load_returns_none_on_version_mismatch(self, tmp_path):
        TaskCache.save(tmp_path, {"t": {"help": "", "args": None}}, "1.0.0")
        assert TaskCache.load(tmp_path, "2.0.0") is None

    def test_load_returns_none_on_corrupt_file(self, tmp_path):
        cache_dir = tmp_path / ".quickie_cache"
        cache_dir.mkdir()
        (cache_dir / "task_names.json").write_text("not json{{{")
        assert TaskCache.load(tmp_path, "1.0.0") is None

    def test_load_returns_none_when_stale(self, tmp_path):
        tasks = {"t": {"help": "", "args": None}}
        TaskCache.save(tmp_path, tasks, "1.0.0")

        # Touch a .py file to make cache stale
        time.sleep(0.05)
        (tmp_path / "new_task.py").write_text("# new")
        os.utime(tmp_path / "new_task.py", (time.time(), time.time()))

        assert TaskCache.load(tmp_path, "1.0.0") is None

    def test_gitignore_created(self, tmp_path):
        TaskCache.save(tmp_path, {}, "1.0.0")
        gitignore = tmp_path / ".quickie_cache" / ".gitignore"
        assert gitignore.exists()
        content = gitignore.read_text()
        assert content == "*\n"

    def test_gitignore_not_overwritten(self, tmp_path):
        TaskCache.save(tmp_path, {}, "1.0.0")
        gitignore = tmp_path / ".quickie_cache" / ".gitignore"
        gitignore.write_text("custom\n")
        # Save again — should not overwrite
        TaskCache.save(tmp_path, {}, "1.0.0")
        assert gitignore.read_text() == "custom\n"

    def test_hidden_dirs_ignored_by_staleness(self, tmp_path):
        """Changes inside .quickie_cache should not invalidate the cache."""
        TaskCache.save(tmp_path, {"t": {"help": "", "args": None}}, "1.0.0")

        # Write into .quickie_cache — should NOT make it stale
        time.sleep(0.05)
        (tmp_path / ".quickie_cache" / "extra.txt").write_text("data")

        result = TaskCache.load(tmp_path, "1.0.0")
        assert result is not None


# ---------------------------------------------------------------------------
# build_cache_entry
# ---------------------------------------------------------------------------


class TestBuildCacheEntry:
    def test_task_without_args(self):
        task = _StubTask("build", "Build the project")
        entry = build_cache_entry(task)
        assert entry["help"] == "Build the project"
        assert entry["args"] is None

    def test_task_with_args(self):
        task = _StubTask(
            "test",
            "Run tests",
            args=[
                {"flags": ["-m", "--marker"], "choices": ["smoke", "unit"]},
                {"flags": ["file"], "nargs": "?"},
            ],
        )
        entry = build_cache_entry(task)
        assert entry["help"] == "Run tests"
        assert entry["args"] is not None
        assert len(entry["args"]["schema"]) == 2
        assert entry["args"]["has_unknown_completers"] is False


# ---------------------------------------------------------------------------
# rebuild_parser
# ---------------------------------------------------------------------------


class TestRebuildParser:
    def test_rebuild_with_choices(self):
        cached_args = {
            "schema": [
                {
                    "flags": ["-m", "--marker"],
                    "dest": "marker",
                    "type": "str",
                    "choices": ["smoke", "unit"],
                    "required": False,
                    "nargs": None,
                    "help": "Test marker",
                    "completer_type": None,
                }
            ],
            "has_unknown_completers": False,
        }
        parser = rebuild_parser("test", cached_args)
        ns = parser.parse_args(["-m", "smoke"])
        assert ns.marker == "smoke"

    def test_rebuild_with_positional(self):
        cached_args = {
            "schema": [
                {
                    "flags": ["file"],
                    "dest": "file",
                    "type": "str",
                    "choices": None,
                    "required": False,
                    "nargs": "?",
                    "help": "Test file",
                    "completer_type": None,
                }
            ],
            "has_unknown_completers": False,
        }
        parser = rebuild_parser("test", cached_args)
        ns = parser.parse_args(["myfile.py"])
        assert ns.file == "myfile.py"

    def test_rebuild_with_path_completer(self):
        cached_args = {
            "schema": [
                {
                    "flags": ["path"],
                    "dest": "path",
                    "type": "str",
                    "choices": None,
                    "required": False,
                    "nargs": None,
                    "help": None,
                    "completer_type": "PathCompleter",
                }
            ],
            "has_unknown_completers": False,
        }
        parser = rebuild_parser("test", cached_args)
        action = [a for a in parser._actions if a.dest == "path"][0]
        from quickie.completion import PathCompleter

        assert isinstance(action.completer, PathCompleter)

    def test_rebuild_with_pytest_completer(self):
        cached_args = {
            "schema": [
                {
                    "flags": ["target"],
                    "dest": "target",
                    "type": "str",
                    "choices": None,
                    "required": False,
                    "nargs": None,
                    "help": None,
                    "completer_type": "PytestCompleter",
                }
            ],
            "has_unknown_completers": False,
        }
        parser = rebuild_parser("test", cached_args)
        action = [a for a in parser._actions if a.dest == "target"][0]
        from quickie.completion.python import PytestCompleter

        assert isinstance(action.completer, PytestCompleter)


# ---------------------------------------------------------------------------
# _detect_completer_type
# ---------------------------------------------------------------------------


class TestDetectCompleterType:
    def test_no_completer(self):
        import argparse

        action = argparse.Action(option_strings=[], dest="x")
        assert _detect_completer_type(action) is None

    def test_path_completer(self):
        import argparse

        from quickie.completion import PathCompleter

        action = argparse.Action(option_strings=[], dest="x")
        action.completer = PathCompleter()
        assert _detect_completer_type(action) == "PathCompleter"

    def test_unknown_completer(self):
        import argparse

        action = argparse.Action(option_strings=[], dest="x")
        action.completer = lambda *a, **kw: []
        assert _detect_completer_type(action) == "function"
