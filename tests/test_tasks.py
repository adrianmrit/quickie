import io

import pytest

import quickie.namespace
from quickie import tasks
from quickie.factories import arg, command, script, task


class TestGlobalNamespace:
    def test_register(self):
        class MyTask(tasks.Task):
            pass

        root_namespace = quickie.namespace.RootNamespace()
        root_namespace.register(MyTask, "mytask")
        assert root_namespace.get_task_class("mytask") is MyTask


class TestNamespace:
    def test_register(self):
        class MyTask(tasks.Task):
            pass

        class MyTask2(tasks.Task):
            pass

        class MyTask3(tasks.Task):
            pass

        root_namespace = quickie.namespace.RootNamespace()
        namespace = quickie.namespace.Namespace("tests", parent=root_namespace)
        namespace.register(MyTask, "mytask")
        namespace.register(MyTask, "alias")
        namespace.register(MyTask2, "mytask2")
        sub_namespace = quickie.namespace.Namespace("sub", parent=namespace)
        sub_namespace.register(MyTask3, "mytask3")

        assert root_namespace.get_task_class("tests:mytask") is MyTask
        assert root_namespace.get_task_class("tests:alias") is MyTask
        assert root_namespace.get_task_class("tests:mytask2") is MyTask2
        assert root_namespace.get_task_class("tests:sub:mytask3") is MyTask3
        assert sub_namespace.get_task_class("mytask3") is MyTask3


class TestTask:
    def test_parser(self, context):
        @task(extra_args=True)
        @arg("arg1")
        @arg("--arg2", "-a2")
        def my_task(*args, **kwargs):
            return args, kwargs

        task_instance = my_task(context=context)

        result = task_instance(["value1", "--arg2", "value2", "value3"])
        assert result == (("value3",), {"arg1": "value1", "arg2": "value2"})

        my_task._meta.extra_args = False

        with pytest.raises(SystemExit) as exc_info:
            task_instance(["value1", "--arg2", "value2", "value3"])
        assert exc_info.value.code == 2

        result = task_instance(["value1", "--arg2", "value2"])
        assert result == ((), {"arg1": "value1", "arg2": "value2"})

    def test_help(self, context):
        class Task1(tasks.Task):
            """Some documentation"""

            def add_args(self, parser):
                parser.add_argument("arg1")
                parser.add_argument("--arg2", "-a2")

        class Task2(Task1):
            pass

        task_1 = Task1("task", context=context)
        task_2 = Task2(context=context)

        assert (
            task_1.get_help()
            == f"usage: {context.program_name} task [-h] [--arg2 ARG2] arg1\n"
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
            f"usage: {context.program_name} Task2 [-h] [--arg2 ARG2] arg1\n"
            "\n"
            "positional arguments:\n"
            "  arg1\n"
            "\n"
            "options:\n"
            "  -h, --help            show this help message and exit\n"
            "  --arg2 ARG2, -a2 ARG2\n"
        )

    def test_run_required(self, context):
        class MyTask(tasks.Task):
            pass

        task_instance = MyTask(context=context)
        with pytest.raises(NotImplementedError):
            task_instance.run()

    def test_print(self, context):
        class MyTask(tasks.Task):
            pass

        context.console.file = io.StringIO()
        task_instance = MyTask(context=context)
        task_instance.print("Hello world!")

        assert context.console.file.getvalue() == "Hello world!\n"

    def test_printe(self, context):
        class MyTask(tasks.Task):
            pass

        context.console.file = io.StringIO()
        task_instance = MyTask(context=context)
        task_instance.print_error("Hello world!")

        out = context.console.file.getvalue()
        assert "Hello world!" in out
        assert out.endswith("\n")


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
    def test_cwd(self, attr, expected, context):
        context.cwd = "/example/cwd"

        class MyTask(tasks.BaseSubprocessTask):
            cwd = attr

        task_instance = MyTask(context=context)
        assert task_instance.get_cwd() == expected

    def test_env(self, context):
        context.env = {"MYENV": "myvalue"}

        class MyTask(tasks.BaseSubprocessTask):
            env = {"OTHERENV": "othervalue"}

        task_instance = MyTask(context=context)
        assert task_instance.get_env() == {"MYENV": "myvalue", "OTHERENV": "othervalue"}


class TestCommand:
    def test_run(self, mocker, context):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.return_value = mocker.Mock(returncode=0)

        context.cwd = "/example/cwd"
        context.env = {"MYENV": "myvalue"}

        @command(cwd="../other", env={"OTHERENV": "othervalue"})
        def my_task():
            return ["myprogram"]

        class TaskWithArgs(tasks.Command):
            binary = "myprogram"
            args = ["arg1", "arg2"]

        @command(cwd="/full/path", env={"MYENV": "myvalue"})
        @arg("--arg1")
        def dynamic_args_task(arg1):
            return ["myprogram", arg1]

        task_instance = my_task(context=context)
        task_with_args = TaskWithArgs(context=context)
        task_with_dynamic_args = dynamic_args_task(context=context)

        task_instance([])
        subprocess_run.assert_called_once_with(
            ["myprogram"],
            check=False,
            cwd="/example/other",
            env={"MYENV": "myvalue", "OTHERENV": "othervalue"},
        )
        subprocess_run.reset_mock()

        task_with_args([])
        subprocess_run.assert_called_once_with(
            ["myprogram", "arg1", "arg2"],
            check=False,
            cwd="/example/cwd",
            env={"MYENV": "myvalue"},
        )
        subprocess_run.reset_mock()

        task_with_dynamic_args(["--arg1", "value1"])
        subprocess_run.assert_called_once_with(
            ["myprogram", "value1"],
            check=False,
            cwd="/full/path",
            env={"MYENV": "myvalue"},
        )
        subprocess_run.reset_mock()

    def test_program_required(self, context):
        class MyTask(tasks.Command):
            pass

        task_instance = MyTask(context=context)
        with pytest.raises(
            NotImplementedError, match="Either set program or override get_program()"
        ):
            task_instance([])


class TestScriptTask:
    def test_run(self, mocker, context):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.return_value = mocker.Mock(returncode=0)

        context.cwd = "/somedir"
        context.env = {"VAR": "VAL"}

        class MyTask(tasks.Script):
            script = "myscript"

        @arg("arg1")
        @script
        def dynamic_script(*, arg1):
            return "myscript " + arg1

        task_instance = MyTask(context=context)
        dynamic_task = dynamic_script(context=context)

        task_instance([])
        subprocess_run.assert_called_once_with(
            "myscript",
            check=False,
            shell=True,
            cwd="/somedir",
            env={"VAR": "VAL"},
        )
        subprocess_run.reset_mock()

        dynamic_task(["value1"])
        subprocess_run.assert_called_once_with(
            "myscript value1",
            check=False,
            shell=True,
            cwd="/somedir",
            env={"VAR": "VAL"},
        )

    def test_script_required(self, context):
        class MyTask(tasks.Script):
            pass

        task_instance = MyTask(context=context)
        with pytest.raises(
            NotImplementedError, match="Either set script or override get_script()"
        ):
            task_instance([])


class TestSerialTaskGroup:
    def test_run(self, context):
        result = []

        @task
        def task_1():
            result.append("First")

        class Task2(tasks.Task):
            def run(self, **kwargs):
                result.append("Second")

        class MyTask(tasks.Group):
            task_classes = [task_1, Task2]

        task_instance = MyTask(context=context)
        task_instance([])

        assert result == ["First", "Second"]


class TestThreadTaskGroup:
    def test_run(self, context):
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

        class MyTask(tasks.ThreadGroup):
            task_classes = [Task1, Task2]

        task_instance = MyTask(context=context)
        task_instance([])
        assert result == ["First", "Second", "Third"]
