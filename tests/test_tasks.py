import functools

import pytest

import quickie._namespace
from quickie import tasks, app
from quickie.conditions import condition
from quickie.context import Context
from quickie.factories import command, group, script, task, thread_group


class TestGlobalNamespace:
    def test_register(self):
        class MyTask(tasks.Task):
            pass

        root_namespace = quickie._namespace.RootNamespace()
        root_namespace.register(MyTask, namespace="mytask")
        assert root_namespace["mytask"] is MyTask


class TestTask:
    def test_parser(self):
        @task(
            args=[
                "arg1",
                ("--arg2", "-a2"),
            ],
            extra_args=True,
        )
        def my_task(*args, **kwargs):
            return args, kwargs

        task_instance = my_task()

        result = task_instance.parse_and_run(["value1", "--arg2", "value2", "value3"])
        assert result == (("value3",), {"arg1": "value1", "arg2": "value2"})

        my_task.extra_args = False  # type: ignore

        with pytest.raises(SystemExit) as exc_info:
            task_instance.parse_and_run(["value1", "--arg2", "value2", "value3"])
        assert exc_info.value.code == 2

        result = task_instance.parse_and_run(["value1", "--arg2", "value2"])
        assert result == ((), {"arg1": "value1", "arg2": "value2"})

    def test_run_required(self):
        class MyTask(tasks.Task):
            pass

        task_instance = MyTask()
        with pytest.raises(NotImplementedError):
            task_instance.run()

    def test_before_after_and_cleanup(self):
        result = []

        @task
        def other(arg):
            result.append(arg)

        app.tasks.register(other, namespace="other")
        app.tasks.register(other, namespace="namespaced.other")

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

        app.tasks.register(defined_later, namespace="defined_later")

        task_instance = my_task()
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

    def test_cleanup_on_errors(self):
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

        task_instance = taskA()
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

        task_instance = taskB()
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

        task_instance = taskC()
        result = []
        with pytest.raises(MyError):
            task_instance()

        assert result == [
            "before",
            "cleanup",
        ]

    def test_cache(self):
        counter = 0

        @task
        @functools.cache
        def my_task(a, b):
            nonlocal counter
            counter += 1
            return a + b

        # initialize multiple times, as this is what might happen in practice
        assert my_task().__call__(1, 2) == 3  # noqa: PLR2004
        assert my_task().__call__(1, 2) == 3  # noqa: PLR2004
        assert counter == 1
        assert my_task().__call__(2, 3) == 5  # noqa: PLR2004
        assert counter == 2  # noqa: PLR2004

        # Does not work because self changes every time
        # @task(bind=True)
        # @functools.cache
        # def my_other_task(self, a, b):
        #     nonlocal counter
        #     counter += 1
        #     return a + b

        # assert my_other_task(context=context).__call__(1, 2) == 3  # noqa: PLR2004
        # assert my_other_task(context=context).__call__(1, 2) == 3  # noqa: PLR2004
        # assert counter == 3  # noqa: PLR2004
        # assert my_other_task(context=context).__call__(2, 3) == 5  # noqa: PLR2004
        # assert counter == 4  # noqa: PLR2004

    def test_condition(self):
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
            a_and_b()()
            a_or_b()()
            not_a()()
            a_xor_b()()

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
    def test_cwd(self, attr, expected, mocker):
        mocker.patch(
            "quickie.context.Context.default",
            return_value=Context(cwd="/example/cwd", env={}),
        )

        class MyTask(tasks._BaseSubprocessTask):
            cwd = attr

        task_instance = MyTask()
        assert task_instance.get_cwd() == expected

    def test_env(self, mocker):
        mocker.patch(
            "quickie.context.Context.default",
            return_value=Context(cwd="", env={"MYENV": "myvalue"}, inherit_env=False),
        )

        class MyTask(tasks._BaseSubprocessTask):
            env = {"OTHERENV": "othervalue"}

        task_instance = MyTask()
        assert task_instance.get_env() == {
            "MYENV": "myvalue",
            "OTHERENV": "othervalue",
        }


class TestCommand:
    def test_run(self, mocker):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.return_value = mocker.Mock(returncode=0)

        mocker.patch(
            "quickie.context.Context.default",
            return_value=Context(cwd="/example/cwd", env={}, inherit_env=False),
        )

        @command(cwd="../other", env={"OTHERENV": "othervalue"})
        def my_task():
            return ["myprogram"]

        @command(cwd="../other", env={"OTHERENV": "othervalue"})
        def task_with_string():
            return 'myprogram arg1 arg2 "arg3 with spaces"'

        class TaskWithArgs(tasks.Command):
            binary = "myprogram"
            cmd_args = ["arg1", "arg2"]

        @command(cwd="/full/path", env={"MYENV": "myvalue"}, args=["--arg1"])
        def dynamic_args_task(arg1):
            return ["myprogram", arg1]

        task_instance = my_task()
        cmd_with_string_instance = task_with_string()
        task_with_args = TaskWithArgs()
        task_with_dynamic_args = dynamic_args_task()

        task_instance()
        assert subprocess_run.call_count == 1
        assert subprocess_run.call_args[0][0] == ["myprogram"]
        assert subprocess_run.call_args[1]["check"] is False
        assert subprocess_run.call_args[1]["cwd"] == "/example/other"
        assert subprocess_run.call_args[1]["env"] == {"OTHERENV": "othervalue"}
        subprocess_run.reset_mock()

        cmd_with_string_instance()
        assert subprocess_run.call_count == 1
        assert subprocess_run.call_args[0][0] == [
            "myprogram",
            "arg1",
            "arg2",
            "arg3 with spaces",
        ]
        assert subprocess_run.call_args[1]["check"] is False
        assert subprocess_run.call_args[1]["cwd"] == "/example/other"
        assert subprocess_run.call_args[1]["env"] == {"OTHERENV": "othervalue"}
        subprocess_run.reset_mock()

        task_with_args([])
        assert subprocess_run.call_count == 1
        assert subprocess_run.call_args[0][0] == ["myprogram", "arg1", "arg2"]
        assert subprocess_run.call_args[1]["check"] is False
        assert subprocess_run.call_args[1]["cwd"] == "/example/cwd"
        assert subprocess_run.call_args[1]["env"] == {}
        subprocess_run.reset_mock()

        task_with_dynamic_args.parse_and_run(["--arg1", "value1"])
        assert subprocess_run.call_count == 1
        assert subprocess_run.call_args[0][0] == ["myprogram", "value1"]
        assert subprocess_run.call_args[1]["check"] is False
        assert subprocess_run.call_args[1]["cwd"] == "/full/path"
        assert subprocess_run.call_args[1]["env"] == {"MYENV": "myvalue"}
        subprocess_run.reset_mock()

    def test_program_required(self):
        class MyTask(tasks.Command):
            pass

        task_instance = MyTask()
        with pytest.raises(
            NotImplementedError, match="Either set program or override get_program()"
        ):
            task_instance([])


class TestScriptTask:
    def test_run(self, mocker):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.return_value = mocker.Mock(returncode=0)

        mocker.patch(
            "quickie.context.Context.default",
            return_value=Context(cwd="/somedir", env={}, inherit_env=False),
        )

        class MyTask(tasks.Script):
            script = "myscript"

        @script(args=["arg1"], env={"VAR": "VAL"})
        def dynamic_script(*, arg1):
            return "myscript " + arg1

        task_instance = MyTask()
        dynamic_task = dynamic_script()

        task_instance([])
        subprocess_run.assert_called_once_with(
            "myscript",
            check=False,
            shell=True,
            cwd="/somedir",
            env={},
            executable=None,
        )
        subprocess_run.reset_mock()

        dynamic_task.parse_and_run(["value1"])
        subprocess_run.assert_called_once_with(
            "myscript value1",
            check=False,
            shell=True,
            cwd="/somedir",
            env={"VAR": "VAL"},
            executable=None,
        )

    def test_script_required(self):
        class MyTask(tasks.Script):
            pass

        task_instance = MyTask()
        with pytest.raises(
            NotImplementedError, match="Either set script or override get_script()"
        ):
            task_instance([])


class TestSerialTaskGroup:
    def test_run(self):
        result = []

        @task(bind=True)
        def task_1(self, arg):
            result.append(arg)

        class Task2(tasks.Task):
            def run(self):
                result.append("Second")

        @group(args=["arg"])
        def my_group(arg):
            return [tasks.partial_task(task_1, arg), Task2]

        task_instance = my_group()
        task_instance.parse_and_run(["First"])

        assert result == ["First", "Second"]


class TestThreadTaskGroup:
    def test_run(self):
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

        task_instance = my_task()
        task_instance()
        assert result == ["First", "Second", "Third"]
