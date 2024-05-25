import io
import os
import sys
from argparse import ArgumentParser
from typing import Any

import pytest

import task_mom.namespace
from task_mom import tasks
from task_mom.context import Context


class TestGlobalNamespace:
    def test_register(self):
        class MyTask(tasks.Task):
            pass

        task_mom.namespace.global_namespace.register(MyTask, "mytask")
        assert task_mom.namespace.get_task_class("mytask") is MyTask


class TestNamespace:
    def test_register(self):
        class MyTask(tasks.Task):
            pass

        class MyTask2(tasks.Task):
            pass

        class MyTask3(tasks.Task):
            pass

        namespace = task_mom.namespace.Namespace("tests")
        namespace.register(MyTask, "mytask")
        namespace.register(MyTask, "alias")
        namespace.register(MyTask2, "mytask2")
        sub_namespace = task_mom.namespace.Namespace("sub", parent=namespace)
        sub_namespace.register(MyTask3, "mytask3")

        assert task_mom.namespace.get_task_class("tests:mytask") is MyTask
        assert task_mom.namespace.get_task_class("tests:alias") is MyTask
        assert task_mom.namespace.get_task_class("tests:mytask2") is MyTask2
        assert task_mom.namespace.get_task_class("tests:sub:mytask3") is MyTask3
        assert sub_namespace.get_task_class("mytask3") is MyTask3


class TestTask:
    def test_parser(self):
        @tasks.allow_unknown_args
        class MyTask(tasks.Task):
            def add_args(self, parser):
                parser.add_argument("arg1")
                parser.add_argument("--arg2", "-a2")

            def run(self, *args, **kwargs):
                return args, kwargs

        task = MyTask()

        result = task(["value1", "--arg2", "value2", "value3"])
        assert result == (("value3",), {"arg1": "value1", "arg2": "value2"})

        tasks.disallow_unknown_args(MyTask)

        with pytest.raises(SystemExit) as exc_info:
            task(["value1", "--arg2", "value2", "value3"])
        assert exc_info.value.code == 2

        result = task(["value1", "--arg2", "value2"])
        assert result == ((), {"arg1": "value1", "arg2": "value2"})

    def test_help(self):
        class Task1(tasks.Task):
            """Some documentation"""

            def add_args(self, parser):
                parser.add_argument("arg1")
                parser.add_argument("--arg2", "-a2")

        class Task2(Task1):
            pass

        task_1 = Task1("task")
        task_2 = Task2()

        assert (
            task_1.get_help()
            == f"usage: {os.path.basename(sys.argv[0])} task [-h] [--arg2 ARG2] arg1\n"
            "\n"
            "Some documentation\n"
            "\n"
            "positional arguments:\n"
            "  arg1\n"
            "\n"
            "options:\n"
            "  -h, --help            show this help message and exit\n"
            "  --arg2 ARG2, -a2 ARG2\n"
        )

        assert task_2.get_help() == (
            f"usage: {os.path.basename(sys.argv[0])} Task2 [-h] [--arg2 ARG2] arg1\n"
            "\n"
            "positional arguments:\n"
            "  arg1\n"
            "\n"
            "options:\n"
            "  -h, --help            show this help message and exit\n"
            "  --arg2 ARG2, -a2 ARG2\n"
        )

    def test_run_required(self):
        class MyTask(tasks.Task):
            pass

        task = MyTask()
        with pytest.raises(NotImplementedError):
            task.run()

    def test_writeln(self):
        stdout = io.StringIO()
        stderr = io.StringIO()

        class MyTask(tasks.Task):
            pass

        context = Context(stdout=stdout, stderr=stderr)
        task = MyTask(context=context)
        task.writeln("Hello world!")

        assert stdout.getvalue() == "Hello world!\n"
        assert stderr.getvalue() == ""

    def test_errorln(self):
        stdout = io.StringIO()
        stderr = io.StringIO()

        context = Context(stdout=stdout, stderr=stderr)

        class MyTask(tasks.Task):
            pass

        task = MyTask(context=context)
        task.errorln("Hello world!")

        assert stdout.getvalue() == ""
        assert stderr.getvalue() == "Hello world!\n"

    def test_input(self):
        # New pipe for stdin
        stdin = io.StringIO()
        stdout = io.StringIO()
        stderr = io.StringIO()

        context = Context(stdin=stdin, stdout=stdout, stderr=stderr)
        stdin.write("value1\n")
        stdin.seek(0)

        class MyTask(tasks.Task):
            pass

        task = MyTask(context=context)
        result = task.input("Prompt message")
        assert result == "value1"
        assert stdout.getvalue() == "Prompt message"
        assert not stderr.getvalue()

        # No input on non required field
        stdin.write("\n")
        result = task.input("Prompt message", required=False)
        assert result == ""


class TestBaseSubprocessTask:
    @pytest.mark.parametrize(
        "attr,expected",
        [
            ("../other", "/example/other"),
            ("other", "/example/cwd/other"),
            ("/absolute", "/absolute"),
            ("./relative", "/example/cwd/relative"),
            ("", "/example/cwd"),
            (None, "/example/cwd"),
        ],
    )
    def test_cwd(self, attr, expected):
        context = Context(cwd="/example/cwd")

        class MyTask(tasks.BaseSubprocessTask):
            cwd = attr

        task = MyTask(context=context)
        assert task.get_cwd() == expected

    def test_env(self):
        context = Context(env={"MYENV": "myvalue"})

        class MyTask(tasks.BaseSubprocessTask):
            env = {"OTHERENV": "othervalue"}

        task = MyTask(context=context)
        assert task.get_env() == {"MYENV": "myvalue", "OTHERENV": "othervalue"}


class TestProgramTask:
    def test_run(self, mocker):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.return_value = mocker.Mock(returncode=0)

        stdin = io.StringIO()
        stdout = io.StringIO()
        stderr = io.StringIO()
        context = Context(
            cwd="/example/cwd",
            env={"MYENV": "myvalue"},
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
        )

        class MyTask(tasks.ProgramTask):
            program = "myprogram"
            cwd = "../other"
            env = {"OTHERENV": "othervalue"}

        class TaskWithArgs(tasks.ProgramTask):
            program = "myprogram"
            program_args = ["arg1", "arg2"]

        class TaskWithDynamicArgs(tasks.ProgramTask):
            cwd = "/full/path"

            def get_program(self, **kwargs: dict[str, Any]) -> str:
                return "myprogram"

            def add_args(self, parser: ArgumentParser):
                super().add_args(parser)
                parser.add_argument("--arg1")

            def get_program_args(self, **kwargs):
                return [kwargs["arg1"]]

        task = MyTask(context=context)
        task_with_args = TaskWithArgs(context=context)
        task_with_dynamic_args = TaskWithDynamicArgs(context=context)

        task([])
        subprocess_run.assert_called_once_with(
            ["myprogram"],
            check=False,
            cwd="/example/other",
            env={"MYENV": "myvalue", "OTHERENV": "othervalue"},
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
        )
        subprocess_run.reset_mock()

        task_with_args([])
        subprocess_run.assert_called_once_with(
            ["myprogram", "arg1", "arg2"],
            check=False,
            cwd="/example/cwd",
            env={"MYENV": "myvalue"},
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
        )
        subprocess_run.reset_mock()

        task_with_dynamic_args(["--arg1", "value1"])
        subprocess_run.assert_called_once_with(
            ["myprogram", "value1"],
            check=False,
            cwd="/full/path",
            env={"MYENV": "myvalue"},
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
        )
        subprocess_run.reset_mock()

    def test_program_required(self):
        class MyTask(tasks.ProgramTask):
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

        class NamedStringIO(io.StringIO):
            def __init__(self, name):
                super().__init__()
                self.name = name

            def __repr__(self):
                return f"<{self.name}>"

        stdin = io.StringIO()
        stdout = io.StringIO()
        stderr = io.StringIO()

        context = Context(
            cwd="/somedir",
            env={"VAR": "VAL"},
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
        )

        class MyTask(tasks.ScriptTask):
            script = "myscript"

        class DynamicScript(tasks.ScriptTask):
            def add_args(self, parser):
                super().add_args(parser)
                parser.add_argument("arg1")

            def get_script(self, **kwargs):
                return "myscript " + kwargs["arg1"]

        task = MyTask(context=context)
        dynamic_task = DynamicScript(context=context)

        task([])
        subprocess_run.assert_called_once_with(
            "myscript",
            check=False,
            shell=True,
            cwd="/somedir",
            env={"VAR": "VAL"},
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
        )
        subprocess_run.reset_mock()

        dynamic_task(["value1"])
        subprocess_run.assert_called_once_with(
            "myscript value1",
            check=False,
            shell=True,
            cwd="/somedir",
            env={"VAR": "VAL"},
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
        )
        subprocess_run.reset_mock()

    def test_script_required(self):
        class MyTask(tasks.ScriptTask):
            pass

        task = MyTask()
        with pytest.raises(
            NotImplementedError, match="Either set script or override get_script()"
        ):
            task([])


class TestSerialTaskGroup:
    def test_run(self, mocker):
        result = []

        class Task1(tasks.Task):
            def run(self, **kwargs):
                result.append("First")

        class Task2(tasks.Task):
            def run(self, **kwargs):
                result.append("Second")

        class MyTask(tasks.SerialTaskGroup):
            task_classes = [Task1, Task2]

        task = MyTask()
        task([])

        assert result == ["First", "Second"]


class TestThreadTaskGroup:
    def test_run(self, mocker):
        result = []

        class Task1(tasks.Task):
            def run(self, **kwargs):
                while not result:  # Wait for Task2 to append
                    pass
                result.append("Second")

        class Task2(tasks.Task):
            def run(self, **kwargs):
                result.append("First")
                while not len(result) == 2:  # Wait for Task1 to finish
                    pass
                result.append("Third")

        class MyTask(tasks.ThreadTaskGroup):
            task_classes = [Task1, Task2]

        task = MyTask()
        task([])
        assert result == ["First", "Second", "Third"]
