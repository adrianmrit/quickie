from quickie import task, tasks, app
from quickie._namespace import RootNamespace
from quickie.completion._internal import TaskCompleter
from quickie.completion.python import PytestCompleter


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
