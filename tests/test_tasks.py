import sys
from argparse import ArgumentParser
from typing import Any

import pytest

from task_mom.tasks import (
    Namespace,
    ProgramTask,
    ScriptTask,
    SerialTaskGroup,
    Task,
    ThreadTaskGroup,
    get_task_class,
    global_namespace,
    register,
)


class TestGlobalNamespace:
    def test_register(self):
        @register
        @register("alias")
        class MyTask(Task):
            pass

        assert get_task_class("mytask") is MyTask
        assert get_task_class("alias") is MyTask

    def test_register_namespace(self):
        @global_namespace.register
        class MyTask(Task):
            pass

        assert get_task_class("mytask") is MyTask
        assert global_namespace.get_task_class("mytask") is MyTask


class TestNamespace:
    def test_register(self):
        namespace = Namespace("tests")

        @namespace.register
        @namespace.register("alias")
        class MyTask(Task):
            pass

        @namespace.register
        class MyTask2(Task):
            pass

        sub_namespace = Namespace("sub", parent=namespace)

        @sub_namespace.register
        class MyTask3(Task):
            pass

        assert get_task_class("tests.mytask") is MyTask
        assert get_task_class("tests.alias") is MyTask
        assert get_task_class("tests.mytask2") is MyTask2
        assert get_task_class("tests.sub.mytask3") is MyTask3
        assert sub_namespace.get_task_class("mytask3") is MyTask3

    def test_invalid_register(self):
        namespace = Namespace("tests")

        with pytest.raises(TypeError, match="Expected a Task class"):
            namespace.register("invalid", name="alias")


class TestTask:
    def test_parser(self):
        class MyTask(Task):
            def add_arguments(self, parser):
                parser.add_argument("arg1")
                parser.add_argument("--arg2", "-a2")

            def run(self, **kwargs):
                return kwargs

        task = MyTask()

        result = task(["value1", "--arg2", "value2"])
        assert result == {"arg1": "value1", "arg2": "value2"}

    def test_help(self):
        class Task1(Task):
            """Some documentation"""

            def add_arguments(self, parser):
                parser.add_argument("arg1")
                parser.add_argument("--arg2", "-a2")

        class Task2(Task1):
            pass

        task_1 = Task1("task")
        task_2 = Task2()

        assert (
            task_1.get_help() == "usage: task [--arg2 ARG2] arg1\n"
            "\n"
            "Some documentation\n"
            "\n"
            "positional arguments:\n"
            "  arg1\n"
            "\n"
            "options:\n"
            "  --arg2 ARG2, -a2 ARG2\n"
        )

        assert task_2.get_help() == (
            "usage: Task2 [--arg2 ARG2] arg1\n"
            "\n"
            "positional arguments:\n"
            "  arg1\n"
            "\n"
            "options:\n"
            "  --arg2 ARG2, -a2 ARG2\n"
        )

    def test_run_required(self):
        class MyTask(Task):
            pass

        task = MyTask()
        with pytest.raises(NotImplementedError):
            task.run()


class TestProgramTask:
    def test_run(self, mocker):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.return_value = mocker.Mock(returncode=0)

        class MyTask(ProgramTask):
            program = "myprogram"

        class TaskWithArgs(ProgramTask):
            program = "myprogram"
            program_args = ["arg1", "arg2"]

        class TaskWithDynamicArgs(ProgramTask):
            def get_program(self, **kwargs: dict[str, Any]) -> str:
                return "myprogram"

            def add_arguments(self, parser: ArgumentParser):
                super().add_arguments(parser)
                parser.add_argument("--arg1")

            def get_program_args(self, **kwargs):
                return [kwargs["arg1"]]

        task = MyTask()
        task_with_args = TaskWithArgs()
        task_with_dynamic_args = TaskWithDynamicArgs()

        task([])
        subprocess_run.assert_called_once_with(
            ["myprogram"],
            check=False,
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        subprocess_run.reset_mock()

        task_with_args([])
        subprocess_run.assert_called_once_with(
            ["myprogram", "arg1", "arg2"],
            check=False,
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        subprocess_run.reset_mock()

        task_with_dynamic_args(["--arg1", "value1"])
        subprocess_run.assert_called_once_with(
            ["myprogram", "value1"],
            check=False,
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        subprocess_run.reset_mock()

    def test_program_required(self):
        class MyTask(ProgramTask):
            pass

        task = MyTask()
        with pytest.raises(
            NotImplementedError, match="Either set program or override get_program()"
        ):
            task([])


class TestScriptTask:
    def test_run(self, mocker):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.return_value = mocker.Mock(returncode=0)

        class MyTask(ScriptTask):
            script = "myscript"

        class DynamicScript(ScriptTask):
            def add_arguments(self, parser):
                super().add_arguments(parser)
                parser.add_argument("arg1")

            def get_script(self, **kwargs):
                return "myscript " + kwargs["arg1"]

        task = MyTask()
        dynamic_task = DynamicScript()

        task([])
        subprocess_run.assert_called_once_with(
            "myscript",
            check=False,
            shell=True,
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        subprocess_run.reset_mock()

        dynamic_task(["value1"])
        subprocess_run.assert_called_once_with(
            "myscript value1",
            check=False,
            shell=True,
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        subprocess_run.reset_mock()

    def test_script_required(self):
        class MyTask(ScriptTask):
            pass

        task = MyTask()
        with pytest.raises(
            NotImplementedError, match="Either set script or override get_script()"
        ):
            task([])


class TestSerialTaskGroup:
    def test_run(self, mocker):
        result = []

        class Task1(Task):
            def run(self, **kwargs):
                result.append("First")

        class Task2(Task):
            def run(self, **kwargs):
                result.append("Second")

        class MyTask(SerialTaskGroup):
            task_classes = [Task1, Task2]

        task = MyTask()
        task([])

        assert result == ["First", "Second"]


class TestThreadTaskGroup:
    def test_run(self, mocker):
        result = []

        class Task1(Task):
            def run(self, **kwargs):
                while not result:  # Wait for Task2 to append
                    pass
                result.append("Second")

        class Task2(Task):
            def run(self, **kwargs):
                result.append("First")
                while not len(result) == 2:  # Wait for Task1 to finish
                    pass
                result.append("Third")

        class MyTask(ThreadTaskGroup):
            task_classes = [Task1, Task2]

        task = MyTask()
        task([])
        assert result == ["First", "Second", "Third"]
