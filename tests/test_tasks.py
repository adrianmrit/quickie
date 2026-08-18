import functools
import io
import sys
import types
from unittest.mock import PropertyMock

import pytest

import quickie._namespace
from quickie import tasks, app
from quickie.conditions import condition
from quickie.context import Context
from quickie.errors import (
    SubprocessExitCodeError,
    SubprocessTimeoutError,
    TaskNotFoundError,
)
from quickie.factories import (
    command,
    group,
    script,
    task,
    task_factory_helper,
    thread_group,
)
from quickie.tasks import MAX_SHORT_HELP_LENGTH, OutputMode, identifier_to_task_name


class TestGlobalNamespace:
    def test_register(self):
        class MyTask(tasks.Task):
            pass

        root_namespace = quickie._namespace.RootNamespace()
        root_namespace.register(MyTask(), namespace="mytask")
        assert isinstance(root_namespace["mytask"], MyTask)


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

        result = my_task.parse_and_run(["value1", "--arg2", "value2", "value3"])
        assert result == (("value3",), {"arg1": "value1", "arg2": "value2"})

        my_task.extra_args = False  # type: ignore

        with pytest.raises(SystemExit) as exc_info:
            my_task.parse_and_run(["value1", "--arg2", "value2", "value3"])
        assert exc_info.value.code == 2

        result = my_task.parse_and_run(["value1", "--arg2", "value2"])
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

        @task(
            before=[
                functools.partial(other, "before"),
                lambda: defined_later("before2"),
            ],
            after=[
                lambda: other("after"),
                functools.partial(other, "after2"),
            ],
            cleanup=[
                functools.partial(other, "cleanup"),
                functools.partial(other, "cleanup2"),
            ],
        )
        def my_task():
            result.append("Task result")

        @task
        def defined_later(arg):
            result.append(f"{arg} defined later")

        my_task()

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
                functools.partial(task_without_error, "before"),
                task_with_error,
            ],
            after=[
                functools.partial(task_without_error, "after"),
            ],
            cleanup=[
                functools.partial(task_without_error, "cleanup"),
            ],
        )
        def taskA():
            result.append("Task result")

        with pytest.raises(MyError):
            taskA()

        assert result == [
            "before",
            "cleanup",
        ]

        @task(
            before=[
                functools.partial(task_without_error, "before"),
            ],
            after=[
                functools.partial(task_without_error, "after"),
                task_with_error,
                functools.partial(task_without_error, "after2"),
            ],
            cleanup=[
                functools.partial(task_without_error, "cleanup"),
            ],
        )
        def taskB():
            result.append("Task result")

        result = []
        with pytest.raises(MyError):
            taskB()

        assert result == [
            "before",
            "Task result",
            "after",
            "cleanup",
        ]

        @task(
            before=[
                functools.partial(task_without_error, "before"),
            ],
            after=[
                functools.partial(task_without_error, "after"),
                functools.partial(task_without_error, "after2"),
            ],
            cleanup=[
                functools.partial(task_without_error, "cleanup"),
            ],
        )
        def taskC():
            raise MyError("An error occurred")

        result = []
        with pytest.raises(MyError):
            taskC()

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
        assert my_task(1, 2) == 3  # noqa: PLR2004
        assert my_task(1, 2) == 3  # noqa: PLR2004
        assert counter == 1
        assert my_task(2, 3) == 5  # noqa: PLR2004
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
            a_and_b()
            a_or_b()
            not_a()
            a_xor_b()

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

    def test_watch_attributes_defaults(self):
        """Task class defaults for watch attributes."""

        @task
        def my_task():
            pass

        assert my_task.watch_paths == ()
        assert my_task.watch_exclude == ()
        assert my_task.watch_debounce is None
        assert my_task.watch_interval is None

    def test_watch_attributes_via_decorator(self):
        """@task decorator passes watch configuration to the task."""

        @task(
            watch_paths=["src/"],
            watch_exclude=["tests/"],
            watch_debounce=1.0,
            watch_interval=0.5,
        )
        def my_task():
            pass

        assert list(my_task.watch_paths) == ["src/"]
        assert list(my_task.watch_exclude) == ["tests/"]
        assert my_task.watch_debounce == 1.0
        assert my_task.watch_interval == 0.5

    def test_watch_attributes_via_script_decorator(self):
        """@script passes watch configuration to the task."""

        @script(
            watch_paths=["src/"],
            watch_exclude=["tests/"],
            watch_debounce=1.0,
            watch_interval=0.5,
        )
        def my_script():
            return "echo test"

        assert list(my_script.watch_paths) == ["src/"]
        assert list(my_script.watch_exclude) == ["tests/"]
        assert my_script.watch_debounce == 1.0
        assert my_script.watch_interval == 0.5

    def test_watch_attributes_via_command_decorator(self):
        """@command passes watch configuration to the task."""

        @command(watch_paths=["src/"], watch_debounce=1.0)
        def my_command():
            return ["echo", "test"]

        assert list(my_command.watch_paths) == ["src/"]
        assert my_command.watch_debounce == 1.0

    def test_watch_attributes_via_class(self):
        """Task subclasses can define watch configuration as class attributes."""

        class MyTask(tasks.Task):
            watch_paths = ["lib/"]
            watch_exclude = [".venv"]
            watch_debounce = 2.0
            watch_interval = 0.1

        t = MyTask()
        assert list(t.watch_paths) == ["lib/"]
        assert list(t.watch_exclude) == [".venv"]
        assert t.watch_debounce == 2.0
        assert t.watch_interval == 0.1

    def test_watch_attributes_override(self):
        """Constructor args override class-level watch defaults."""

        class MyTask(tasks.Task):
            watch_paths = ["src/"]

        t = MyTask(watch_paths=["lib/"], watch_debounce=1.5)
        assert list(t.watch_paths) == ["lib/"]
        assert t.watch_debounce == 1.5


class TestBaseSubprocessTask:
    @pytest.mark.parametrize(
        "attr,expected",
        [
            ("../other", "/example/other"),
            ("other", "/example/cwd/other"),
            ("/absolute", "/absolute"),
            ("./relative", "/example/project/relative"),
            ("", "/example/cwd"),
            (None, "/example/cwd"),
        ],
    )
    def test_wd(self, attr, expected, mocker):
        from pathlib import Path

        mocker.patch.object(app, "context", Context(wd="/example/cwd", env={}))
        mocker.patch.object(
            type(app),
            "tasks_path",
            new_callable=PropertyMock,
            return_value=Path("/example/project/_qk"),
        )

        class MyTask(tasks._BaseSubprocessTask):
            wd = attr

        task_instance = MyTask()
        assert task_instance.get_wd() == expected

    def test_env(self, mocker):
        mocker.patch.object(
            app,
            "context",
            Context(wd="", env={"MYENV": "myvalue"}, inherit_env=False),
        )

        class MyTask(tasks._BaseSubprocessTask):
            env = {"OTHERENV": "othervalue"}

        task_instance = MyTask()
        assert task_instance.get_env() == {
            "MYENV": "myvalue",
            "OTHERENV": "othervalue",
        }

    def test_env_file_loaded_at_runtime(self, mocker, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("FILE_VAR=from_file\n")

        mocker.patch.object(
            app,
            "context",
            Context(wd="", env={}, inherit_env=False),
        )
        mocker.patch.object(
            type(app),
            "tasks_path",
            new_callable=PropertyMock,
            return_value=tmp_path / "_qk",
        )

        task_instance = tasks._BaseSubprocessTask(env_file=str(env_file))
        assert task_instance.get_env()["FILE_VAR"] == "from_file"

    def test_env_file_relative_resolves_from_tasks_root(self, mocker, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("RELATIVE_VAR=yes\n")

        mocker.patch.object(
            app,
            "context",
            Context(wd="", env={}, inherit_env=False),
        )
        # tasks_path = tmp_path/_qk  → parent = tmp_path
        mocker.patch.object(
            type(app),
            "tasks_path",
            new_callable=PropertyMock,
            return_value=tmp_path / "_qk",
        )

        task_instance = tasks._BaseSubprocessTask(env_file=".env")
        assert task_instance.get_env()["RELATIVE_VAR"] == "yes"

    def test_explicit_env_overrides_env_file(self, mocker, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=from_file\n")

        mocker.patch.object(
            app,
            "context",
            Context(wd="", env={}, inherit_env=False),
        )
        mocker.patch.object(
            type(app),
            "tasks_path",
            new_callable=PropertyMock,
            return_value=tmp_path / "_qk",
        )

        task_instance = tasks._BaseSubprocessTask(
            env={"KEY": "explicit"}, env_file=str(env_file)
        )
        assert task_instance.get_env()["KEY"] == "explicit"

    def test_env_file_via_command_decorator(self, mocker, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("DECO_VAR=deco_value\n")

        mocker.patch.object(
            app,
            "context",
            Context(wd="", env={}, inherit_env=False),
        )
        mocker.patch.object(
            type(app),
            "tasks_path",
            new_callable=PropertyMock,
            return_value=tmp_path / "_qk",
        )

        @command(env_file=str(env_file))
        def my_task():
            return ["echo"]

        assert my_task.get_env()["DECO_VAR"] == "deco_value"

    def test_run(self, mocker):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.return_value = mocker.Mock(returncode=0)

        mocker.patch.object(
            app,
            "context",
            Context(wd="/example/cwd", env={}, inherit_env=False),
        )

        @command(wd="../other", env={"OTHERENV": "othervalue"})
        def my_task():
            return ["myprogram"]

        @command(wd="../other", env={"OTHERENV": "othervalue"})
        def task_with_string():
            return 'myprogram arg1 arg2 "arg3 with spaces"'

        @task
        class TaskWithArgs(tasks.Command):
            binary = "myprogram"
            cmd_args = ["arg1", "arg2"]

        @command(wd="/full/path", env={"MYENV": "myvalue"}, args=["--arg1"])
        def dynamic_args_task(arg1):
            return ["myprogram", arg1]

        my_task()
        assert subprocess_run.call_count == 1
        assert subprocess_run.call_args[0][0] == ["myprogram"]
        assert subprocess_run.call_args[1]["check"] is False
        assert subprocess_run.call_args[1]["cwd"] == "/example/other"
        assert subprocess_run.call_args[1]["env"] == {"OTHERENV": "othervalue"}
        subprocess_run.reset_mock()

        task_with_string()
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

        TaskWithArgs([])
        assert subprocess_run.call_count == 1
        assert subprocess_run.call_args[0][0] == ["myprogram", "arg1", "arg2"]
        assert subprocess_run.call_args[1]["check"] is False
        assert subprocess_run.call_args[1]["cwd"] == "/example/cwd"
        assert subprocess_run.call_args[1]["env"] == {}
        subprocess_run.reset_mock()

        dynamic_args_task.parse_and_run(["--arg1", "value1"])
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

    def test_run_resolves_python_to_venv_executable_early(self, mocker):
        """python binary is resolved to sys.executable before subprocess is called."""
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.return_value = mocker.Mock(returncode=0)

        mocker.patch.object(
            app,
            "context",
            Context(wd="/example/cwd", env={}, inherit_env=False),
        )
        mocker.patch("quickie.tasks.os.path.exists", return_value=True)
        mocker.patch("quickie.tasks.sys.executable", "/venv/bin/python")

        @command
        def my_task():
            return ["python", "-m", "pytest"]

        my_task()

        # Only one subprocess call — resolution happened before it, not as a retry
        assert subprocess_run.call_count == 1
        assert subprocess_run.call_args_list[0].args[0] == [
            "/venv/bin/python",
            "-m",
            "pytest",
        ]

    def test_run_uses_original_python_when_no_fallback_found(self, mocker):
        """When no fallback is resolvable, python is used as-is."""
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.return_value = mocker.Mock(returncode=0)

        mocker.patch.object(
            app,
            "context",
            Context(wd="/example/cwd", env={}, inherit_env=False),
        )
        mocker.patch("quickie.tasks.os.path.exists", return_value=False)
        mocker.patch("quickie.tasks.shutil.which", return_value=None)

        @command
        def my_task():
            return ["python", "-m", "pytest"]

        my_task()

        assert subprocess_run.call_args_list[0].args[0] == ["python", "-m", "pytest"]

    def test_run_raises_when_non_python_binary_is_missing(self, mocker):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.side_effect = FileNotFoundError("myprogram")

        mocker.patch.object(
            app,
            "context",
            Context(wd="/example/cwd", env={}, inherit_env=False),
        )

        @command
        def my_task():
            return ["myprogram", "--version"]

        with pytest.raises(FileNotFoundError):
            my_task()


class TestScriptTask:
    def test_run(self, mocker):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.return_value = mocker.Mock(returncode=0)

        mocker.patch.object(
            app,
            "context",
            Context(wd="/somedir", env={}, inherit_env=False),
        )

        class MyTask(tasks.Script):
            script = "myscript"

        @script(args=["arg1"], env={"VAR": "VAL"})
        def dynamic_script(*, arg1):
            return "myscript " + arg1

        task_instance = MyTask()

        task_instance([])
        subprocess_run.assert_called_once_with(
            "myscript",
            shell=True,
            check=False,
            cwd="/somedir",
            env=mocker.ANY,
            executable=None,
            timeout=None,
            capture_output=False,
        )
        subprocess_run.reset_mock()

        dynamic_script.parse_and_run(["value1"])
        subprocess_run.assert_called_once_with(
            "myscript value1",
            shell=True,
            check=False,
            cwd="/somedir",
            env=mocker.ANY,
            executable=None,
            timeout=None,
            capture_output=False,
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

        @task
        class Task2(tasks.Task):
            def run(self):
                result.append("Second")

        @group(args=["arg"])
        def my_group(arg):
            return [functools.partial(task_1, arg), Task2]

        my_group.parse_and_run(["First"])

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
            return [Task1(), functools.partial(task2, "Third")]

        my_task()
        assert result == ["First", "Second", "Third"]

    def test_exception_propagation(self):
        class FailingTask(tasks.Task):
            def run(self):
                raise ValueError("thread error")

        @thread_group
        def my_group():
            return [FailingTask()]

        with pytest.raises(ExceptionGroup) as exc_info:
            my_group()
        assert len(exc_info.value.exceptions) == 1
        assert isinstance(exc_info.value.exceptions[0], ValueError)
        assert str(exc_info.value.exceptions[0]) == "thread error"

    def test_multiple_failures_all_aggregated(self):
        """All exceptions from failing tasks are collected, none silently dropped."""
        import threading

        barrier = threading.Barrier(2)

        class FailingTask(tasks.Task):
            def __init__(self, msg):
                super().__init__()
                self.msg = msg

            def run(self):
                barrier.wait()
                raise ValueError(self.msg)

        @thread_group
        def my_group():
            return [FailingTask("error1"), FailingTask("error2")]

        with pytest.raises(ExceptionGroup) as exc_info:
            my_group()
        messages = {str(e) for e in exc_info.value.exceptions}
        assert messages == {"error1", "error2"}

    def test_all_tasks_complete_on_failure(self):
        """Every sibling task runs to completion even when another task raises."""
        import threading

        barrier = threading.Barrier(2)
        completed = []

        class FailingTask(tasks.Task):
            def run(self):
                barrier.wait()
                raise ValueError("fail")

        @task
        def passing_task():
            barrier.wait()
            completed.append("done")

        @thread_group
        def my_group():
            return [FailingTask(), passing_task]

        with pytest.raises(ExceptionGroup):
            my_group()
        assert completed == ["done"]


def test_identifier_to_task_name():
    assert identifier_to_task_name("MyTask") == "mytask"
    assert identifier_to_task_name("my_task") == "my-task"
    assert identifier_to_task_name("My__Task_") == "my-task"
    assert identifier_to_task_name("_private_") == "private"
    assert identifier_to_task_name("simple") == "simple"
    assert identifier_to_task_name("ALLCAPS") == "allcaps"


class TestTaskExtended:
    def test_skip_inside_run(self):
        from quickie.errors import Skip

        @task
        def my_task():
            raise Skip("skipping this")

        # Skip raised inside run() is caught by full_run, not propagated
        result = my_task()
        assert result is None

    def test_cleanup_exception_suppressed(self):
        result = []

        @task
        def failing_cleanup():
            raise ValueError("cleanup failed")

        @task
        def passing_cleanup():
            result.append("ran")

        @task(cleanup=[failing_cleanup, passing_cleanup])
        def main_task():
            pass

        # Should not raise despite failing_cleanup; passing_cleanup still runs
        main_task()
        assert result == ["ran"]

    def test_double_dash_extra_args(self):
        @task(extra_args=True)
        def my_task(*args):
            return args

        result = my_task.parse_and_run(["--", "extra1", "extra2"])
        assert result == ("extra1", "extra2")

    def test_string_in_before(self, mocker):
        result = []

        @task
        def before_task():
            result.append("before")

        tasks_ns = quickie._namespace.RootNamespace()
        tasks_ns.register(before_task, namespace="before-task")
        mocker.patch("quickie.app._tasks", tasks_ns)

        @task(before=["before-task"])
        def main_task():
            result.append("main")

        main_task()
        assert result == ["before", "main"]

    def test_get_short_help_truncation(self):
        long_doc = "A" * 60  # longer than MAX_SHORT_HELP_LENGTH = 50

        class MyTask(tasks.Task):
            def run(self):
                pass

        MyTask.__doc__ = long_doc
        t = MyTask()
        short = t.get_short_help()
        assert len(short) == MAX_SHORT_HELP_LENGTH
        assert short.endswith("...")

    def test_get_short_help_multiline(self):
        class MyTask(tasks.Task):
            """First paragraph summary.

            Second paragraph detail that should be ignored.
            """

            def run(self):
                pass

        t = MyTask()
        short = t.get_short_help()
        assert short == "First paragraph summary."
        assert "Second" not in short

    def test_aliases_registered(self):
        module = types.SimpleNamespace()

        @task(aliases=["h", "hello-alias"])
        def hello():
            pass

        module.__dict__["hello"] = hello

        ns = quickie._namespace.RootNamespace()
        ns.load(module)

        assert ns["hello"] is hello
        assert ns["h"] is hello
        assert ns["hello-alias"] is hello

    def test_private_excluded_from_load(self):
        module = types.SimpleNamespace()

        @task(private=True)
        def private_task():
            pass

        module.__dict__["private_task"] = private_task

        ns = quickie._namespace.RootNamespace()
        ns.load(module)

        assert len(ns) == 0
        with pytest.raises(TaskNotFoundError):
            ns["private-task"]


class TestBaseSubprocessTaskExtended:
    def test_wd_dot_uses_tasks_path_parent(self, mocker):
        from pathlib import Path

        mocker.patch(
            "quickie.app._project_path", Path("/abs/tasks_module"), create=True
        )

        class MyTask(tasks._BaseSubprocessTask):
            wd = "."

        assert MyTask().get_wd() == "/abs"


class TestCommandExtended:
    def test_empty_cmd_raises(self, mocker):
        mocker.patch.object(
            app, "context", Context(wd="/tmp", env={}, inherit_env=False)
        )

        class EmptyCmd(tasks.Command):
            def get_cmd(self, *args, **kwargs):
                return []

        with pytest.raises(ValueError, match="No program to run"):
            EmptyCmd()([])

    def test_non_zero_exit_code_raises(self, mocker):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.return_value = mocker.Mock(returncode=7)

        mocker.patch.object(
            app,
            "context",
            Context(wd="/example/cwd", env={}, inherit_env=False),
        )

        @command
        def my_task():
            return ["myprogram", "--fail"]

        with pytest.raises(SubprocessExitCodeError, match="exit code 7") as exc_info:
            my_task()

        assert exc_info.value.exit_code == 7
        assert subprocess_run.call_args[1]["check"] is False

    def test_expected_exit_codes_allow_non_zero_result(self, mocker):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.return_value = mocker.Mock(returncode=7)

        mocker.patch.object(
            app,
            "context",
            Context(wd="/example/cwd", env={}, inherit_env=False),
        )

        @command(expected_exit_codes=(0, 7))
        def my_task():
            return ["myprogram", "--fail"]

        result = my_task()

        assert result.returncode == 7
        assert subprocess_run.call_args[1]["check"] is False

    @pytest.mark.parametrize("expected_exit_codes", [None, ()])
    def test_disable_exit_code_validation(self, mocker, expected_exit_codes):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.return_value = mocker.Mock(returncode=7)

        mocker.patch.object(
            app,
            "context",
            Context(wd="/example/cwd", env={}, inherit_env=False),
        )

        @command(expected_exit_codes=expected_exit_codes)
        def my_task():
            return ["myprogram", "--fail"]

        result = my_task()

        assert result.returncode == 7
        assert subprocess_run.call_args[1]["check"] is False

    def test_timeout_raises_subprocess_timeout_error(self, mocker):
        import subprocess as sp

        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.side_effect = sp.TimeoutExpired(cmd="myprogram", timeout=5)

        mocker.patch.object(
            app,
            "context",
            Context(wd="/example/cwd", env={}, inherit_env=False),
        )

        @command(timeout=5)
        def my_task():
            return ["myprogram", "--long"]

        with pytest.raises(SubprocessTimeoutError) as exc_info:
            my_task()

        assert exc_info.value.timeout == 5
        assert "myprogram" in str(exc_info.value)
        assert subprocess_run.call_args[1]["timeout"] == 5

    def test_timeout_passed_to_subprocess(self, mocker):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.return_value = mocker.Mock(returncode=0)

        mocker.patch.object(
            app,
            "context",
            Context(wd="/example/cwd", env={}, inherit_env=False),
        )

        @command(timeout=10.0)
        def my_task():
            return ["myprogram"]

        my_task()

        assert subprocess_run.call_args[1]["timeout"] == 10.0

    def test_retries_on_exit_code_error(self, mocker):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.side_effect = [
            mocker.Mock(returncode=1),
            mocker.Mock(returncode=0),
        ]

        mocker.patch.object(
            app,
            "context",
            Context(wd="/example/cwd", env={}, inherit_env=False),
        )

        @command(retries=1)
        def my_task():
            return ["myprogram"]

        result = my_task()

        assert result.returncode == 0
        assert subprocess_run.call_count == 2  # noqa: PLR2004

    def test_retries_exhausted_raises_last_error(self, mocker):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.return_value = mocker.Mock(returncode=1)

        mocker.patch.object(
            app,
            "context",
            Context(wd="/example/cwd", env={}, inherit_env=False),
        )

        @command(retries=2)
        def my_task():
            return ["myprogram"]

        with pytest.raises(SubprocessExitCodeError):
            my_task()

        assert subprocess_run.call_count == 3  # noqa: PLR2004

    def test_retries_on_timeout(self, mocker):
        import subprocess as sp

        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.side_effect = [
            sp.TimeoutExpired(cmd="myprogram", timeout=2),
            mocker.Mock(returncode=0),
        ]

        mocker.patch.object(
            app,
            "context",
            Context(wd="/example/cwd", env={}, inherit_env=False),
        )

        @command(timeout=2, retries=1)
        def my_task():
            return ["myprogram"]

        result = my_task()

        assert result.returncode == 0
        assert subprocess_run.call_count == 2  # noqa: PLR2004

    def test_retry_delay_sleeps_between_attempts(self, mocker):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.side_effect = [
            mocker.Mock(returncode=1),
            mocker.Mock(returncode=0),
        ]
        time_sleep = mocker.patch("time.sleep")

        mocker.patch.object(
            app,
            "context",
            Context(wd="/example/cwd", env={}, inherit_env=False),
        )

        @command(retries=1, retry_delay=2.0)
        def my_task():
            return ["myprogram"]

        my_task()

        time_sleep.assert_called_once_with(2.0)

    def test_no_sleep_when_retry_delay_is_zero(self, mocker):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.side_effect = [
            mocker.Mock(returncode=1),
            mocker.Mock(returncode=0),
        ]
        time_sleep = mocker.patch("time.sleep")

        mocker.patch.object(
            app,
            "context",
            Context(wd="/example/cwd", env={}, inherit_env=False),
        )

        @command(retries=1)
        def my_task():
            return ["myprogram"]

        my_task()

        time_sleep.assert_not_called()

    def test_retry_logs_warning_on_failure(self, mocker):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.side_effect = [
            mocker.Mock(returncode=1),
            mocker.Mock(returncode=0),
        ]
        logger_warning = mocker.patch.object(app.logger, "warning")

        mocker.patch.object(
            app,
            "context",
            Context(wd="/example/cwd", env={}, inherit_env=False),
        )

        @command(retries=1)
        def my_task():
            return ["myprogram"]

        my_task()

        # Should log: attempt N failed + retrying
        assert logger_warning.call_count == 2  # noqa: PLR2004

    def test_capture_output_mode(self, mocker):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.return_value = mocker.Mock(
            returncode=0, stdout=b"output", stderr=b""
        )

        mocker.patch.object(
            app,
            "context",
            Context(wd="/example/cwd", env={}, inherit_env=False),
        )

        @command(output_mode=OutputMode.CAPTURE)
        def my_task():
            return ["myprogram"]

        result = my_task()

        assert subprocess_run.call_args[1]["capture_output"] is True
        assert result.stdout == b"output"

    def test_capture_output_mode_string_literal(self, mocker):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.return_value = mocker.Mock(
            returncode=0, stdout=b"output", stderr=b""
        )

        mocker.patch.object(
            app,
            "context",
            Context(wd="/example/cwd", env={}, inherit_env=False),
        )

        @command(output_mode="capture")
        def my_task():
            return ["myprogram"]

        result = my_task()

        assert subprocess_run.call_args[1]["capture_output"] is True
        assert result.stdout == b"output"

    def test_tee_output_mode(self, mocker):
        mock_process = mocker.Mock()
        mock_process.stdout.read1.side_effect = [b"hello\n", b""]
        mock_process.stderr.read1.side_effect = [b"err\n", b""]
        mock_process.returncode = 0
        mock_process.wait.return_value = None

        mock_popen = mocker.patch("subprocess.Popen", return_value=mock_process)
        subprocess_run = mocker.patch("subprocess.run")

        mocker.patch.object(
            app,
            "context",
            Context(wd="/example/cwd", env={}, inherit_env=False),
        )
        mocker.patch.object(sys, "stdout", mocker.Mock(buffer=io.BytesIO()))
        mocker.patch.object(sys, "stderr", mocker.Mock(buffer=io.BytesIO()))

        @command(output_mode=OutputMode.TEE)
        def my_task():
            return ["myprogram"]

        result = my_task()

        mock_popen.assert_called_once()
        subprocess_run.assert_not_called()
        assert result.stdout == b"hello\n"
        assert result.stderr == b"err\n"
        assert result.returncode == 0

    def test_tee_output_mode_streams_to_terminal(self, mocker):
        mock_process = mocker.Mock()
        mock_process.stdout.read1.side_effect = [b"hello\n", b""]
        mock_process.stderr.read1.side_effect = [b""]
        mock_process.returncode = 0
        mock_process.wait.return_value = None

        mocker.patch("subprocess.Popen", return_value=mock_process)

        mocker.patch.object(
            app,
            "context",
            Context(wd="/example/cwd", env={}, inherit_env=False),
        )
        stdout_buf = io.BytesIO()
        mocker.patch.object(sys, "stdout", mocker.Mock(buffer=stdout_buf))
        mocker.patch.object(sys, "stderr", mocker.Mock(buffer=io.BytesIO()))

        @command(output_mode=OutputMode.TEE)
        def my_task():
            return ["myprogram"]

        my_task()

        assert stdout_buf.getvalue() == b"hello\n"

    def test_tee_output_mode_timeout(self, mocker):
        import subprocess as sp

        mock_process = mocker.Mock()
        mock_process.stdout.read1.return_value = b""
        mock_process.stderr.read1.return_value = b""
        mock_process.wait.side_effect = sp.TimeoutExpired(cmd="myprogram", timeout=5)

        mocker.patch("subprocess.Popen", return_value=mock_process)

        mocker.patch.object(
            app,
            "context",
            Context(wd="/example/cwd", env={}, inherit_env=False),
        )
        mocker.patch.object(sys, "stdout", mocker.Mock(buffer=io.BytesIO()))
        mocker.patch.object(sys, "stderr", mocker.Mock(buffer=io.BytesIO()))

        @command(output_mode=OutputMode.TEE, timeout=5)
        def my_task():
            return ["myprogram"]

        with pytest.raises(SubprocessTimeoutError) as exc_info:
            my_task()

        assert exc_info.value.timeout == 5
        mock_process.kill.assert_called_once()


class TestScriptTaskExtended:
    def test_non_zero_exit_code_raises(self, mocker):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.return_value = mocker.Mock(returncode=5)

        mocker.patch.object(
            app,
            "context",
            Context(wd="/somedir", env={}, inherit_env=False),
        )

        @script
        def fail_script():
            return "exit 5"

        with pytest.raises(SubprocessExitCodeError, match="exit code 5") as exc_info:
            fail_script()

        assert exc_info.value.exit_code == 5
        assert subprocess_run.call_args[1]["check"] is False

    def test_expected_exit_codes_allow_non_zero_result(self, mocker):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.return_value = mocker.Mock(returncode=5)

        mocker.patch.object(
            app,
            "context",
            Context(wd="/somedir", env={}, inherit_env=False),
        )

        @script(expected_exit_codes=(0, 5))
        def fail_script():
            return "exit 5"

        result = fail_script()

        assert result.returncode == 5
        assert subprocess_run.call_args[1]["check"] is False

    @pytest.mark.parametrize("expected_exit_codes", [None, ()])
    def test_disable_exit_code_validation(self, mocker, expected_exit_codes):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.return_value = mocker.Mock(returncode=5)

        mocker.patch.object(
            app,
            "context",
            Context(wd="/somedir", env={}, inherit_env=False),
        )

        @script(expected_exit_codes=expected_exit_codes)
        def fail_script():
            return "exit 5"

        result = fail_script()

        assert result.returncode == 5
        assert subprocess_run.call_args[1]["check"] is False

    def test_timeout_raises_subprocess_timeout_error(self, mocker):
        import subprocess as sp

        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.side_effect = sp.TimeoutExpired(cmd="exit 5", timeout=3)

        mocker.patch.object(
            app,
            "context",
            Context(wd="/somedir", env={}, inherit_env=False),
        )

        @script(timeout=3)
        def slow_script():
            return "exit 5"

        with pytest.raises(SubprocessTimeoutError) as exc_info:
            slow_script()

        assert exc_info.value.timeout == 3  # noqa: PLR2004
        assert subprocess_run.call_args[1]["timeout"] == 3  # noqa: PLR2004

    def test_retries_on_exit_code_error(self, mocker):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.side_effect = [
            mocker.Mock(returncode=1),
            mocker.Mock(returncode=0),
        ]

        mocker.patch.object(
            app,
            "context",
            Context(wd="/somedir", env={}, inherit_env=False),
        )

        @script(retries=1)
        def flaky_script():
            return "flaky_command"

        result = flaky_script()

        assert result.returncode == 0
        assert subprocess_run.call_count == 2  # noqa: PLR2004

    def test_retries_exhausted_raises_last_error(self, mocker):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.return_value = mocker.Mock(returncode=1)

        mocker.patch.object(
            app,
            "context",
            Context(wd="/somedir", env={}, inherit_env=False),
        )

        @script(retries=2)
        def always_fails():
            return "bad_command"

        with pytest.raises(SubprocessExitCodeError):
            always_fails()

        assert subprocess_run.call_count == 3  # noqa: PLR2004

    def test_retry_delay_sleeps_between_attempts(self, mocker):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.side_effect = [
            mocker.Mock(returncode=1),
            mocker.Mock(returncode=0),
        ]
        time_sleep = mocker.patch("time.sleep")

        mocker.patch.object(
            app,
            "context",
            Context(wd="/somedir", env={}, inherit_env=False),
        )

        @script(retries=1, retry_delay=1.5)
        def flaky_script():
            return "flaky_command"

        flaky_script()

        time_sleep.assert_called_once_with(1.5)

    def test_capture_output_mode(self, mocker):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.return_value = mocker.Mock(
            returncode=0, stdout=b"output", stderr=b""
        )

        mocker.patch.object(
            app,
            "context",
            Context(wd="/somedir", env={}, inherit_env=False),
        )

        @script(output_mode=OutputMode.CAPTURE)
        def my_script():
            return "myprogram"

        result = my_script()

        assert subprocess_run.call_args[1]["capture_output"] is True
        assert result.stdout == b"output"

    def test_capture_output_mode_string_literal(self, mocker):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.return_value = mocker.Mock(
            returncode=0, stdout=b"output", stderr=b""
        )

        mocker.patch.object(
            app,
            "context",
            Context(wd="/somedir", env={}, inherit_env=False),
        )

        @script(output_mode="capture")
        def my_script():
            return "myprogram"

        result = my_script()

        assert subprocess_run.call_args[1]["capture_output"] is True
        assert result.stdout == b"output"

    def test_tee_output_mode(self, mocker):
        mock_process = mocker.Mock()
        mock_process.stdout.read1.side_effect = [b"hello\n", b""]
        mock_process.stderr.read1.side_effect = [b"err\n", b""]
        mock_process.returncode = 0
        mock_process.wait.return_value = None

        mock_popen = mocker.patch("subprocess.Popen", return_value=mock_process)
        subprocess_run = mocker.patch("subprocess.run")

        mocker.patch.object(
            app,
            "context",
            Context(wd="/somedir", env={}, inherit_env=False),
        )
        mocker.patch.object(sys, "stdout", mocker.Mock(buffer=io.BytesIO()))
        mocker.patch.object(sys, "stderr", mocker.Mock(buffer=io.BytesIO()))

        @script(output_mode=OutputMode.TEE)
        def my_script():
            return "myprogram"

        result = my_script()

        mock_popen.assert_called_once()
        subprocess_run.assert_not_called()
        assert result.stdout == b"hello\n"
        assert result.stderr == b"err\n"
        assert result.returncode == 0

    def test_tee_output_mode_timeout(self, mocker):
        import subprocess as sp

        mock_process = mocker.Mock()
        mock_process.stdout.read1.return_value = b""
        mock_process.stderr.read1.return_value = b""
        mock_process.wait.side_effect = sp.TimeoutExpired(cmd="myprogram", timeout=5)

        mocker.patch("subprocess.Popen", return_value=mock_process)

        mocker.patch.object(
            app,
            "context",
            Context(wd="/somedir", env={}, inherit_env=False),
        )
        mocker.patch.object(sys, "stdout", mocker.Mock(buffer=io.BytesIO()))
        mocker.patch.object(sys, "stderr", mocker.Mock(buffer=io.BytesIO()))

        @script(output_mode=OutputMode.TEE, timeout=5)
        def my_script():
            return "myprogram"

        with pytest.raises(SubprocessTimeoutError) as exc_info:
            my_script()

        assert exc_info.value.timeout == 5
        mock_process.kill.assert_called_once()


class TestRootNamespace:
    def test_register_multiple_namespaces(self):
        @task
        def my_task():
            pass

        ns = quickie._namespace.RootNamespace()
        ns.register(my_task, namespace=["alias1", "alias2"])

        assert ns["alias1"] is my_task
        assert ns["alias2"] is my_task

    def test_getitem_missing_raises(self):
        ns = quickie._namespace.RootNamespace()
        with pytest.raises(TaskNotFoundError):
            ns["nonexistent"]

    def test_alias_collision_uses_last_loaded_task(self):
        module = types.SimpleNamespace()

        @task(name="first", aliases=["shared"])
        def first_task():
            pass

        @task(name="shared")
        def second_task():
            pass

        module.__dict__["first_task"] = first_task
        module.__dict__["second_task"] = second_task

        ns = quickie._namespace.RootNamespace()
        ns.load(module)

        assert ns["first"] is first_task
        assert ns["shared"] is second_task

    def test_deep_nested_namespaces_load_all_tasks(self):
        module = types.SimpleNamespace()

        @task(name="alpha")
        def alpha_task():
            pass

        @task(name="beta")
        def beta_task():
            pass

        module.__dict__["namespace"] = quickie._namespace.Namespace(
            {
                "lvl1": {
                    "lvl2": {
                        "lvl3": {
                            "lvl4": [alpha_task, beta_task],
                        }
                    }
                }
            }
        )

        ns = quickie._namespace.RootNamespace()
        ns.load(module)

        assert ns["lvl1:lvl2:lvl3:lvl4:alpha"] is alpha_task
        assert ns["lvl1:lvl2:lvl3:lvl4:beta"] is beta_task

    def test_private_task_can_still_be_registered_explicitly(self):
        @task(private=True, name="private-task")
        def private_task():
            pass

        ns = quickie._namespace.RootNamespace()
        ns.register(private_task, namespace="manual:private")

        assert ns["manual:private"] is private_task


class TestFactories:
    def test_wrong_base_class_raises(self):
        class NotATask:
            pass

        with pytest.raises(TypeError):
            task_factory_helper(NotATask, base=tasks.Task, override_method="run")

    def test_script_executable_passed_to_subprocess(self, mocker):
        subprocess_run = mocker.patch("subprocess.run")
        subprocess_run.return_value = mocker.Mock(returncode=0)
        mocker.patch.object(
            app, "context", Context(wd="/somedir", env={}, inherit_env=False)
        )

        @script(executable="/bin/bash")
        def my_script():
            return "echo hello"

        my_script()
        subprocess_run.assert_called_once()
        assert subprocess_run.call_args[1]["executable"] == "/bin/bash"


class TestTaskFileLocation:
    def test_get_relative_file_location_returns_none_for_builtin(self):
        class MyTask(tasks.Task):
            def run(self):
                pass

        t = MyTask()
        t.__wrapped__ = len  # builtin has no Python source file
        assert t._get_relative_file_location("/tmp") is None


class TestAddArgs:
    def test_add_args_with_arg_instance(self):
        from quickie.utils.argparser import Arg

        @task(args=[Arg("--my-arg")])
        def my_task(my_arg=None):
            return my_arg

        result = my_task.parse_and_run(["--my-arg", "value"])
        assert result == "value"

    def test_add_args_invalid_type_raises(self):
        import argparse

        @task
        def my_task():
            pass

        my_task.args = [42]  # type: ignore[assignment]
        parser = argparse.ArgumentParser()
        with pytest.raises(TypeError, match="Invalid argument type"):
            my_task.add_args(parser)


class TestGroupWithTasksAttr:
    def test_group_class_level_tasks(self):
        result = []

        @task
        def task_a():
            result.append("a")

        @task
        def task_b():
            result.append("b")

        class MyGroup(tasks.Group):
            pass

        MyGroup.tasks = (task_a, task_b)  # type: ignore[assignment]
        MyGroup()()

        assert result == ["a", "b"]


def test_log_task_execution_details_noop():
    class MyTask(tasks.Task):
        def run(self):
            pass

    t = MyTask()
    t.log_task_execution_details("some_arg")
