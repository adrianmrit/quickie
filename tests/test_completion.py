from task_mom import tasks
from task_mom.cli import Main
from task_mom.completion._internal import TaskCompleter
from task_mom.completion.python import PytestCompleter


class TestTaskCompleter:
    def test_complete(self, mocker):
        mocker.patch("task_mom.cli.Main.load_tasks_from_namespace")

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
        main.tasks_namespace.register(MyTask, "task")
        main.tasks_namespace.register(TestTask2, "task2")
        main.tasks_namespace.register(Other, "other")

        completer = TaskCompleter(main)

        completions = completer(prefix="t", action=None, parser=None, parsed_args=None)
        assert completions == {"task": "My task", "task2": "My other task"}

        completions = completer(
            prefix="oth", action=None, parser=None, parsed_args=None
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
            "task_mom.completion.base.PathCompleter.get_pre_filtered_paths",
            return_value=["test.py", "test2.py", "other.py", "other"],
        )
        mocker.patch(
            "task_mom.completion.python.PytestCompleter.read_python_file",
            return_value=python_code,
        )
        completer = PytestCompleter()

        completer.read_python_file = mocker.Mock(return_value=python_code)

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
            "task_mom.completion.base.PathCompleter.get_pre_filtered_paths",
            return_value=["test.py", "test2.py", "other.py", "other"],
        )
        mocker.patch(
            "task_mom.completion.python.PytestCompleter.read_python_file",
            return_value=python_code,
        )
        completer = PytestCompleter()
        completer.read_python_file = mocker.Mock(return_value=python_code)

        completions = completer.complete(
            prefix="test.py::", action=None, parser=None, parsed_args=None
        )
        assert completions == []
