from quickie import task, tasks, app
from quickie._namespace import RootNamespace
from quickie.completion._internal import TaskCompleter
from quickie.completion.python import PytestCompleter
from quickie.completion.base import BaseCompleter
from quickie.errors import TasksModuleNotFoundError
from quickie.completion import PathCompleter
import os
import pytest


class TestTaskCompleter:
    def test_complete(self, mocker):
        mocker.patch("quickie.app._tasks", RootNamespace(), create=True)

        class MyTask(tasks.Task):
            """My task"""

            pass

        class TestTask2(tasks.Task):
            """My other task"""

            pass

        @task
        def other():
            """Another task"""
            pass

        app.tasks.register(MyTask(), namespace="task")
        app.tasks.register(TestTask2(), namespace="task2")
        app.tasks.register(other, namespace="other")

        completer = TaskCompleter()

        completions = completer(prefix="t", action=None, parser=None, parsed_args=None)  # type: ignore
        assert completions == {"task": "My task", "task2": "My other task"}

        completions = completer(
            prefix="oth",
            action=None,
            parser=None,
            parsed_args=None,  # type: ignore
        )
        assert completions == {"other": "Another task"}


class TestPytestCompleter:
    def test_complete(self, mocker):
        python_code = """
class TestClass:
    def test_method(self):
        pass

class NestedClass:
    def other_method(self):
        pass
"""
        mocker.patch(
            "quickie.completion.PathCompleter.get_pre_filtered_paths",
            return_value=["test.py", "test2.py", "other.py", "other"],
        )
        mocker.patch(
            "quickie.completion.python.PytestCompleter._read_python_file",
            return_value=python_code,
        )
        completer = PytestCompleter()

        completions = completer.complete(
            prefix="", action=None, parser=None, parsed_args=None
        )
        assert completions == [
            "test.py",
            "test.py::",
            "test2.py",
            "test2.py::",
            "other.py",
            "other.py::",
            "other",
        ]

        completions = completer.complete(
            prefix="te", action=None, parser=None, parsed_args=None
        )
        assert completions == ["test.py", "test.py::", "test2.py", "test2.py::"]

        completions = completer.complete(
            prefix="test.py::", action=None, parser=None, parsed_args=None
        )
        assert completions == [
            "test.py::TestClass",
            "test.py::TestClass::",
            "test.py::NestedClass",
            "test.py::NestedClass::",
        ]

        completions = completer.complete(
            prefix="test.py::Tes", action=None, parser=None, parsed_args=None
        )
        assert completions == ["test.py::TestClass", "test.py::TestClass::"]

        completions = completer.complete(
            prefix="test.py::NestedClass::", action=None, parser=None, parsed_args=None
        )
        assert completions == ["test.py::NestedClass::other_method"]

        completions = completer.complete(
            prefix="test.py::Invalid::", action=None, parser=None, parsed_args=None
        )
        assert completions == []

    def test_complete_invalid_syntax(self, mocker):
        python_code = """
class TestClass  # invalid syntax
    def test_method(self):
        pass

class NestedClass:
    def other_method(self):
        pass
"""
        mocker.patch(
            "quickie.completion.PathCompleter.get_pre_filtered_paths",
            return_value=["test.py", "test2.py", "other.py", "other"],
        )
        mocker.patch(
            "quickie.completion.python.PytestCompleter._read_python_file",
            return_value=python_code,
        )
        completer = PytestCompleter()

        completions = completer.complete(
            prefix="test.py::", action=None, parser=None, parsed_args=None
        )
        assert completions == []


class TestBaseCompleter:
    def test_complete_raises_not_implemented(self):
        completer = BaseCompleter()
        with pytest.raises(NotImplementedError):
            completer.complete(prefix="", action=None, parser=None, parsed_args=None)  # type: ignore[arg-type]

    def test_call_handles_exception(self, mocker):
        warn_mock = mocker.patch("argcomplete.io.warn")

        completer = BaseCompleter()
        result = completer(prefix="", action=None, parser=None, parsed_args=None)  # type: ignore[arg-type]
        assert result == []
        warn_mock.assert_called_once()


class TestTaskCompleterError:
    def test_complete_suppresses_quickie_error(self, mocker):
        mock_ns = mocker.MagicMock()
        mock_ns.items.side_effect = TasksModuleNotFoundError("_qk")
        mocker.patch("quickie.app._tasks", mock_ns)

        completer = TaskCompleter()
        result = completer(prefix="", action=None, parser=None, parsed_args=None)  # type: ignore[arg-type]
        assert result == {}


class TestPathCompleter:
    def test_get_pre_filtered_paths_handles_error(self):
        completer = PathCompleter()
        result = list(completer.get_pre_filtered_paths("/nonexistent/path/xyz_abc123"))
        assert result == []

    def test_get_pre_filtered_paths_with_wd(self, tmp_path):
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file1.txt").write_text("")
        (subdir / "file2.txt").write_text("")

        completer = PathCompleter(wd=str(tmp_path))
        result = sorted(completer.get_pre_filtered_paths("subdir"))
        assert result == ["file1.txt", "file2.txt"]

    def test_get_pre_filtered_paths_empty_target_uses_wd(self, tmp_path):
        (tmp_path / "foo.txt").write_text("")

        completer = PathCompleter(wd=str(tmp_path))
        result = list(completer.get_pre_filtered_paths(""))
        assert "foo.txt" in result

    def test_absolute_path_ignores_wd(self, tmp_path):
        other_dir = tmp_path / "other"
        other_dir.mkdir()
        (other_dir / "bar.txt").write_text("")

        completer = PathCompleter(wd=str(tmp_path))
        result = list(completer.get_pre_filtered_paths(str(other_dir)))
        assert "bar.txt" in result

    def test_none_wd_falls_back_to_context(self, mocker):
        completer = PathCompleter(wd=None)
        assert completer.get_wd() == os.path.abspath(app.context.wd)


class TestPytestCompleterReadFile:
    def test_read_python_file(self, tmp_path):
        py_file = tmp_path / "test_sample.py"
        py_file.write_text("def test_foo(): pass")

        completer = PytestCompleter()
        content = completer._read_python_file(str(py_file))
        assert "test_foo" in content
