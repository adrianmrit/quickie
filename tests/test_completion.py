from quickie import tasks
from quickie._cli import Main
from quickie.completion._internal import TaskCompleter
from quickie.completion.python import PytestCompleter


class TestTaskCompleter:
    def test_complete(self, mocker):
        mocker.patch("quickie._cli.Main.load_tasks")

        class MyTask(tasks.Task):
            """My task"""

            pass

        class TestTask2(tasks.Task):
            """My other task"""

            pass

        class Other(tasks.Task):
            """Another task"""

            pass

        main = Main(argv=[])
        main.root_namespace.register(MyTask, "task")
        main.root_namespace.register(TestTask2, "task2")
        main.root_namespace.register(Other, "other")

        completer = TaskCompleter(main)

        completions = completer(prefix="t", action=None, parser=None, parsed_args=None)  # type: ignore
        assert completions == {"task": "My task", "task2": "My other task"}

        completions = completer(
            prefix="oth", action=None, parser=None, parsed_args=None  # type: ignore
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
