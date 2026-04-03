"""Tests for quickie.config (App class methods and properties)."""

import pytest

from quickie import app as quickie_app
from quickie.context import Context
from quickie.errors import TasksModuleNotFoundError
from quickie.config import (
    _PlainFormatter,
    TMP_RELATIVE_PATH_ENV,
    LOG_LEVEL_ENV,
    HOME_PATH_ENV,
)
from quickie._version import __version__
from pathlib import Path
import os
import logging


class TestAppSetMethods:
    def test_set_context(self):
        original = quickie_app.context
        try:
            new_ctx = Context(wd="/tmp", env={"X": "1"})
            quickie_app.set_context(new_ctx)
            assert quickie_app.context is new_ctx
        finally:
            quickie_app.context = original

    def test_set_home_path_string(self, tmp_path):
        original = (
            quickie_app._home_path if hasattr(quickie_app, "_home_path") else None
        )
        try:
            quickie_app.set_home_path(str(tmp_path))
            assert quickie_app._home_path == tmp_path
        finally:
            if original is not None:
                quickie_app._home_path = original
            elif hasattr(quickie_app, "_home_path"):
                del quickie_app._home_path

    def test_set_tmp_relative_path_string(self):
        original = (
            quickie_app._tmp_relative_path
            if hasattr(quickie_app, "_tmp_relative_path")
            else None
        )
        try:
            quickie_app.set_tmp_relative_path("my_tmp")
            assert quickie_app._tmp_relative_path == Path("my_tmp")
        finally:
            if original is not None:
                quickie_app._tmp_relative_path = original
            elif hasattr(quickie_app, "_tmp_relative_path"):
                del quickie_app._tmp_relative_path

    def test_configure_valid_key(self, mocker):
        set_verbosity_mock = mocker.patch.object(quickie_app, "set_verbosity")
        quickie_app.configure(verbosity=2)
        set_verbosity_mock.assert_called_once_with(2)

    def test_configure_invalid_key_raises(self):
        with pytest.raises(ValueError, match="Invalid configuration key"):
            quickie_app.configure(nonexistent_key="value")

    def test_tasks_property_raises_when_not_loaded(self):
        had_tasks = hasattr(quickie_app, "_tasks")
        original = quickie_app._tasks if had_tasks else None
        try:
            if had_tasks:
                del quickie_app._tasks
            with pytest.raises(ValueError, match="Tasks not loaded"):
                _ = quickie_app.tasks
        finally:
            if original is not None:
                quickie_app._tasks = original


class TestAppLogFile:
    def test_set_log_file_creates_handler(self, tmp_path, mocker):
        log_file = tmp_path / "test.log"
        original_handlers = list(quickie_app.logger.handlers)
        try:
            quickie_app.set_log_file(str(log_file))
            handler_types = [type(h).__name__ for h in quickie_app.logger.handlers]
            assert "RotatingFileHandler" in handler_types
        finally:
            # Restore original handlers
            for h in list(quickie_app.logger.handlers):
                if h not in original_handlers:
                    quickie_app.logger.removeHandler(h)
                    h.close()

    def test_set_log_file_none_no_handler(self):
        original_log_file = getattr(quickie_app, "log_file", None)
        try:
            quickie_app.set_log_file(None)
            has_file_handler = any(
                isinstance(h, logging.FileHandler) for h in quickie_app.logger.handlers
            )
            assert not has_file_handler
        finally:
            quickie_app.log_file = original_log_file


class TestResolveModulePath:
    def test_finds_py_file(self, tmp_path):
        py_file = tmp_path / "my_tasks.py"
        py_file.write_text("# tasks file")

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = quickie_app._resolve_module_path("my_tasks", traverse=False)
            assert result == py_file
        finally:
            os.chdir(original_cwd)

    def test_not_found_raises(self, tmp_path):
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            with pytest.raises(TasksModuleNotFoundError):
                quickie_app._resolve_module_path(
                    "nonexistent_module_xyz", traverse=False
                )
        finally:
            os.chdir(original_cwd)

    def test_traverse_finds_in_parent(self, tmp_path):
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        tasks_dir = tmp_path / "_qk"
        tasks_dir.mkdir()
        (tasks_dir / "__init__.py").write_text("")

        original_cwd = os.getcwd()
        try:
            os.chdir(subdir)
            result = quickie_app._resolve_module_path("_qk", traverse=True)
            assert result == tasks_dir
        finally:
            os.chdir(original_cwd)


class TestPlainFormatter:
    def test_format_strips_markup(self):
        formatter = _PlainFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="[bold red]Hello[/bold red]",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "[bold red]" not in result
        assert "Hello" in result


class TestAppProperties:
    def test_set_project_path_with_string(self, tmp_path):
        tasks_dir = tmp_path / "_qk"
        tasks_dir.mkdir()
        (tasks_dir / "__init__.py").write_text("")

        original = (
            quickie_app._project_path if hasattr(quickie_app, "_project_path") else None
        )
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            quickie_app.set_project_path("_qk")
            assert quickie_app._project_path == tasks_dir
        finally:
            os.chdir(original_cwd)
            if original is not None:
                quickie_app._project_path = original
            elif hasattr(quickie_app, "_project_path"):
                del quickie_app._project_path

    def test_tasks_path_returns_home_when_global(self):
        original_use_global = (
            quickie_app._use_global if hasattr(quickie_app, "_use_global") else False
        )
        original_home = (
            quickie_app._home_path if hasattr(quickie_app, "_home_path") else None
        )
        try:
            fake_home = Path("/tmp/fake_home")
            quickie_app._home_path = fake_home
            quickie_app._use_global = True
            assert quickie_app.tasks_path == fake_home
        finally:
            quickie_app._use_global = original_use_global
            if original_home is not None:
                quickie_app._home_path = original_home
            elif hasattr(quickie_app, "_home_path"):
                del quickie_app._home_path

    def test_tmp_relative_path_uses_env(self, monkeypatch):
        monkeypatch.setenv(TMP_RELATIVE_PATH_ENV, "custom_tmp")
        original = (
            quickie_app._tmp_relative_path
            if hasattr(quickie_app, "_tmp_relative_path")
            else None
        )
        try:
            if hasattr(quickie_app, "_tmp_relative_path"):
                del quickie_app._tmp_relative_path
            result = quickie_app.tmp_relative_path
            assert result == Path("custom_tmp")
        finally:
            if original is not None:
                quickie_app._tmp_relative_path = original
            elif hasattr(quickie_app, "_tmp_relative_path"):
                del quickie_app._tmp_relative_path

    def test_simple_error_hook(self, capsys):
        quickie_app._simple_error_hook(ValueError, ValueError("test error"), None)
        _, err = capsys.readouterr()
        assert "test error" in err

    def test_set_verbosity_debug_installs_traceback(self, mocker):
        mocker.patch("rich.traceback.install")
        original_level = (
            quickie_app.log_level
            if hasattr(quickie_app, "log_level")
            else logging.WARNING
        )
        try:
            quickie_app.set_verbosity(2)  # -vv sets DEBUG level
            assert quickie_app.log_level == logging.DEBUG
        finally:
            quickie_app.set_verbosity(0)

    def test_set_verbosity_invalid_env_raises(self, monkeypatch):
        monkeypatch.setenv(LOG_LEVEL_ENV, "INVALID_LEVEL")
        with pytest.raises(ValueError, match="Invalid log level"):
            quickie_app.set_verbosity(0)

    def test_home_path_uses_env(self, monkeypatch):
        monkeypatch.setenv(HOME_PATH_ENV, "/tmp/custom_home")
        original = (
            quickie_app._home_path if hasattr(quickie_app, "_home_path") else None
        )
        try:
            if hasattr(quickie_app, "_home_path"):
                del quickie_app._home_path
            result = quickie_app.home_path
            assert result == Path("/tmp/custom_home")
        finally:
            if original is not None:
                quickie_app._home_path = original
            elif hasattr(quickie_app, "_home_path"):
                del quickie_app._home_path

    def test_use_global_defaults_to_false(self):
        original = (
            quickie_app._use_global if hasattr(quickie_app, "_use_global") else None
        )
        try:
            if hasattr(quickie_app, "_use_global"):
                del quickie_app._use_global
            assert quickie_app.use_global is False
        finally:
            if original is not None:
                quickie_app._use_global = original


def test_version_import():
    assert __version__
