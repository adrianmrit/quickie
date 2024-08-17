import functools
import io

import pytest

import quickie._namespace
from quickie import tasks
from quickie.conditions import condition
from quickie.factories import arg, command, group, script, task, thread_group


class TestGlobalNamespace:
    def test_register(self):
        class MyTask(tasks.Task):
            pass

        root_namespace = quickie._namespace.RootNamespace()
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

        root_namespace = quickie._namespace.RootNamespace()
        namespace = quickie._namespace.Namespace("tests", parent=root_namespace)
        namespace.register(MyTask, "mytask")
        namespace.register(MyTask, "alias")
        namespace.register(MyTask2, "mytask2")
        sub_namespace = quickie._namespace.Namespace("sub", parent=namespace)
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

        result = task_instance.parse_and_run(["value1", "--arg2", "value2", "value3"])
        assert result == (("value3",), {"arg1": "value1", "arg2": "value2"})

        my_task.extra_args = False  # type: ignore

        with pytest.raises(SystemExit) as exc_info:
            task_instance.parse_and_run(["value1", "--arg2", "value2", "value3"])
        assert exc_info.value.code == 2

        result = task_instance.parse_and_run(["value1", "--arg2", "value2"])
        assert result == ((), {"arg1": "value1", "arg2": "value2"})

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

    def test_before_after_and_cleanup(self, context):
        result = []

        @task
        def other(arg):
            result.append(arg)

        context.namespace.register(other, "other")
        context.namespace.register(other, "namespaced.other")

        @task(
            before=[
                tasks.partial_task(other, "before"),
                tasks.partial_task("defined_later", "before2"),
            ],
            after=[
                tasks.partial_task("namespaced.other", "after"),
                tasks.partial_task(other, "after2"),
            ],
            cleanup=[
                tasks.partial_task(other, "cleanup"),
                tasks.partial_task(other, "cleanup2"),
            ],
        )
        def my_task():
            result.append("Task result")

        @task
        def defined_later(arg):
            result.append(f"{arg} defined later")

        context.namespace.register(defined_later, "defined_later")

        task_instance = my_task(context=context)
        task_instance()

        assert result == [
            "before",
            "before2 defined later",
            "Task result",
            "after",
            "after2",
            "cleanup",
            "cleanup2",
        ]

    def test_cleanup_on_errors(self, context):
        class MyError(Exception):
            pass

        result = []

        @task
        def task_with_error():
            raise MyError("An error occurred")

        @task
        def task_without_error(arg):
            result.append(arg)

        @task(
            before=[
                tasks.partial_task(task_without_error, "before"),
                task_with_error,
            ],
            after=[
                tasks.partial_task(task_without_error, "after"),
            ],
            cleanup=[
                tasks.partial_task(task_without_error, "cleanup"),
            ],
        )
        def taskA():
            result.append("Task result")

        task_instance = taskA(context=context)
        with pytest.raises(MyError):
            task_instance()

        assert result == [
            "before",
            "cleanup",
        ]

        @task(
            before=[
                tasks.partial_task(task_without_error, "before"),
            ],
            after=[
                tasks.partial_task(task_without_error, "after"),
                task_with_error,
                tasks.partial_task(task_without_error, "after2"),
            ],
            cleanup=[
                tasks.partial_task(task_without_error, "cleanup"),
            ],
        )
        def taskB():
            result.append("Task result")

        task_instance = taskB(context=context)
        result = []
        with pytest.raises(MyError):
            task_instance()

        assert result == [
            "before",
            "Task result",
            "after",
            "cleanup",
        ]

        @task(
            before=[
                tasks.partial_task(task_without_error, "before"),
            ],
            after=[
                tasks.partial_task(task_without_error, "after"),
                tasks.partial_task(task_without_error, "after2"),
            ],
            cleanup=[
                tasks.partial_task(task_without_error, "cleanup"),
            ],
        )
        def taskC():
            raise MyError("An error occurred")

        task_instance = taskC(context=context)
        result = []
        with pytest.raises(MyError):
            task_instance()

        assert result == [
            "before",
            "cleanup",
        ]

    @pytest.mark.xfail(reason="Cache not supported yet when bind=True")
    def test_cache(self, context):
        counter = 0

        @task
        @functools.cache
        def my_task(a, b):
            nonlocal counter
            counter += 1
            return a + b

        # initialize multiple times, as this is what might happen in practice
        assert my_task(context=context).__call__(1, 2) == 3  # noqa: PLR2004
        assert my_task(context=context).__call__(1, 2) == 3  # noqa: PLR2004
        assert counter == 1
        assert my_task(context=context).__call__(2, 3) == 5  # noqa: PLR2004
        assert counter == 2  # noqa: PLR2004

        # should also work if bind=True
        @task(bind=True)
        @functools.cache
        def my_other_task(_, a, b):
            nonlocal counter
            counter += 1
            return a + b

        assert my_other_task(context=context).__call__(1, 2) == 3  # noqa: PLR2004
        assert my_other_task(context=context).__call__(1, 2) == 3  # noqa: PLR2004
        assert counter == 3  # noqa: PLR2004
        assert my_other_task(context=context).__call__(2, 3) == 5  # noqa: PLR2004
        assert counter == 4  # noqa: PLR2004

    def test_condition(self, context):
        result = []

        a_condition = condition(lambda *args, **kwargs: a)
        b_condition = condition(lambda *args, **kwargs: b)

        @task(condition=a_condition & b_condition)
        def a_and_b():
            result.append("a_and_b")

        @task(condition=a_condition | b_condition)
        def a_or_b():
            result.append("a_or_b")

        @task(condition=~a_condition)
        def not_a():
            result.append("not_a")

        @task(condition=a_condition ^ b_condition)
        def a_xor_b():
            result.append("a_xor_b")

        def call_tasks():
            a_and_b(context=context)()
            a_or_b(context=context)()
            not_a(context=context)()
            a_xor_b(context=context)()

        a = False
        b = False
        call_tasks()
        assert result == ["not_a"]

        a = True
        b = False
        result = []
        call_tasks()
        assert result == ["a_or_b", "a_xor_b"]

        a = False
        b = True
        result = []
        call_tasks()
        assert result == ["a_or_b", "not_a", "a_xor_b"]

        a = True
        b = True
        result = []
        call_tasks()
        assert result == ["a_and_b", "a_or_b"]


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

        class MyTask(tasks._BaseSubprocessTask):
            cwd = attr

        task_instance = MyTask(context=context)
        assert task_instance.get_cwd() == expected

    def test_env(self, context):
        context.env = {"MYENV": "myvalue"}

        class MyTask(tasks._BaseSubprocessTask):
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

        task_instance()
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

        task_with_dynamic_args.parse_and_run(["--arg1", "value1"])
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

        dynamic_task.parse_and_run(["value1"])
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

        @task(bind=True)
        def task_1(self, arg):
            result.append(arg)

        class Task2(tasks.Task):
            def run(self):
                result.append("Second")

        @group
        @arg("arg")
        def my_group(arg):
            return [tasks.partial_task(task_1, arg), Task2]

        task_instance = my_group(context=context)
        task_instance.parse_and_run(["First"])

        assert result == ["First", "Second"]


class TestThreadTaskGroup:
    def test_run(self, context):
        result = []

        class Task1(tasks.Task):
            def run(self):
                while not result:  # Wait for Task2 to append
                    pass
                result.append("Second")

        @task
        def task2(arg):
            result.append("First")
            while not len(result) == 2:  # Wait for Task1 to finish  # noqa: PLR2004
                pass
            result.append(arg)

        @thread_group
        def my_task():
            return [Task1, tasks.partial_task(task2, "Third")]

        task_instance = my_task(context=context)
        task_instance()
        assert result == ["First", "Second", "Third"]
