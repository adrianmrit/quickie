from argparse import ArgumentParser
from typing import Any

import pytest

from task_mom.tasks import ProgramTask, ScriptTask, Task


class TestTask:
    def test_meta(self, mocker):
        class MyTask(Task):
            pass

        # Abstract not inherited
        assert Task._meta.abstract is True
        assert MyTask._meta.abstract is False
        # Default Name
        assert MyTask._meta.name == "mytask"

        class MySubTask(MyTask):
            pass

        assert MySubTask._meta.name == "mysubtask"

        class MySubTask2(MyTask):
            class Meta:
                name = "mytask2"
                abstract = True

        assert MySubTask2._meta.name == "mytask2"

        class MySubTask3(MyTask):
            pass

        assert MySubTask3._meta.abstract is False
        assert MySubTask3._meta.name == "mysubtask3"

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

        task_1 = Task1()
        task_2 = Task2()

        assert (
            task_1.get_help() == "usage: task1 [--arg2 ARG2] arg1\n"
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
            "usage: task2 [--arg2 ARG2] arg1\n"
            "\n"
            "positional arguments:\n"
            "  arg1\n"
            "\n"
            "options:\n"
            "  --arg2 ARG2, -a2 ARG2\n"
        )


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
        subprocess_run.assert_called_once_with(["myprogram"], check=False)
        subprocess_run.reset_mock()

        task_with_args([])
        subprocess_run.assert_called_once_with(
            ["myprogram", "arg1", "arg2"], check=False
        )
        subprocess_run.reset_mock()

        task_with_dynamic_args(["--arg1", "value1"])
        subprocess_run.assert_called_once_with(["myprogram", "value1"], check=False)
        subprocess_run.reset_mock()

    def test_error_code_non_0(self, mocker):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.return_value = mocker.Mock(returncode=1)

        class MyTask(ProgramTask):
            program = "myprogram"

        task = MyTask()
        with pytest.raises(RuntimeError, match="Program failed with exit code 1"):
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
        subprocess_run.assert_called_once_with("myscript", check=False, shell=True)
        subprocess_run.reset_mock()

        dynamic_task(["value1"])
        subprocess_run.assert_called_once_with(
            "myscript value1", check=False, shell=True
        )
        subprocess_run.reset_mock()

    def test_error_code_non_0(self, mocker):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.return_value = mocker.Mock(returncode=1)

        class MyTask(ScriptTask):
            script = "myscript"

        task = MyTask()
        with pytest.raises(RuntimeError, match="Script failed with exit code 1"):
            task([])
