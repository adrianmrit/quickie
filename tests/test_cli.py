import os
import re
import subprocess
import sys

import pytest
from pytest import mark, raises

from quickie import _cli
from quickie._argparser import AppArgumentParser
from quickie._namespace import RootNamespace
from quickie.errors import SubprocessExitCodeError
from quickie.errors import Skip, Stop
from quickie.factories import task
from quickie import app as quickie_app

PYTHON_PATH = sys.executable
BIN_FOLDER = os.path.join(sys.prefix, "bin")
BIN_LOCATION = os.path.join(BIN_FOLDER, "qk")


@mark.integration
@mark.parametrize(
    "argv",
    [
        [BIN_LOCATION, "-h"],
        [PYTHON_PATH, "-m", "quickie", "-h", "hello"],
        [PYTHON_PATH, "-m", "quickie", "hello"],
        [PYTHON_PATH, "-m", "quickie", "-h"],
    ],
)  # yapf: disable
def test_from_cli(argv):
    out = subprocess.check_output(argv)
    assert out


@mark.integration
@mark.parametrize(
    "argv",
    [
        ["-h"],
        ["--help"],
    ],
)
def test_help(argv, capsys):
    with raises(SystemExit) as exc_info:
        _cli.main(argv)
    assert exc_info.value.code == 0

    out, err = capsys.readouterr()
    assert "show this help message" in out
    assert not err


@mark.integration
@mark.parametrize(
    "argv",
    [
        ["hello", "-h"],
        ["hello", "--help"],
    ],
)
def test_task_help(argv, capsys):
    with raises(SystemExit) as exc_info:
        _cli.main(argv)
    assert exc_info.value.code == 0

    out, err = capsys.readouterr()
    assert "Hello world task." in out


@mark.integration
@mark.parametrize(
    "argv",
    [
        ["-V"],
        ["--version"],
    ],
)
def test_version(argv, capsys):
    with raises(SystemExit) as exc_info:
        _cli.main(argv)
    assert exc_info.value.code == 0

    out, err = capsys.readouterr()
    assert re.match(r"\d+\.\d+\..*", out)
    assert not err


@mark.integration
def test_default(capsys):
    with raises(SystemExit) as exc_info:
        _cli.main([])
    assert exc_info.value.code == 0
    out, err = capsys.readouterr()
    # normalize spaces in out, as pytest might add extra spaces when running in vscode
    out = re.sub(r"\s+", " ", out)

    assert "[-h]" in out


@mark.integration
def test_fails_find_task():
    with raises(_cli.QuickieError, match="Task 'nonexistent' not found"):
        _cli.main(["nonexistent"], raise_error=True)


@mark.integration
def test_main_no_args(capsys):
    with raises(SystemExit) as exc_info:
        _cli.main([])
    # Depending how we run it we might get a different exit code
    assert exc_info.value.code in (0, 2)
    out, err = capsys.readouterr()
    out = out + err
    # normalize spaces in out, as pytest might add extra spaces when running in vscode
    out = re.sub(r"\s+", " ", out)
    assert "[-h]" in out


@mark.integration
def test_task_not_found(capsys):
    with raises(SystemExit) as exc_info:
        _cli.main(["nonexistent"])
    assert exc_info.value.code == 1
    out, err = capsys.readouterr()
    assert "Task 'nonexistent' not found" in err


@mark.integration
def test_list(capsys):
    with raises(SystemExit) as exc_info:
        _cli.main(["-l"])
    assert exc_info.value.code == 0, str(capsys.readouterr())
    out, err = capsys.readouterr()
    assert "hello" in out
    assert "other-task" in out, f"out: {out}, err: {err}"
    assert "cls_holder:hello" in out, f"out: {out}, err: {err}"
    assert "dict:task:hello" in out, f"out: {out}, err: {err}"
    assert "dict:task:other-ta" in out, f"out: {out}, err: {err}"
    assert "Hello world task." in out

    assert "nested:other" in out, f"out: {out}, err: {err}"
    assert "dict:nested_again" in out, f"out: {out}, err: {err}"
    assert "Other task." in out


@mark.integration
def test_suggest_autocompletion_bash(capsys):
    with raises(SystemExit) as exc_info:
        _cli.main(["--autocomplete", "bash"])
    assert exc_info.value.code == 0
    out, err = capsys.readouterr()
    assert 'eval "$(register-python-argcomplete' in out


@mark.integration
def test_suggest_autocompletion_zsh(capsys):
    with raises(SystemExit) as exc_info:
        _cli.main(["--autocomplete", "zsh"])
    assert exc_info.value.code == 0
    out, err = capsys.readouterr()
    assert 'eval "$(register-python-argcomplete' in out


def test_stop_iteration(capsys, mocker):
    @task
    def stop():
        raise Stop("My message", exit_code=10)

    @task
    def stop_no_reason():
        raise Stop(exit_code=5)

    @task(before=[stop, stop_no_reason])
    def with_before():
        pass

    tasks = RootNamespace()

    tasks.register(stop, namespace="stop")
    tasks.register(stop_no_reason, namespace="stop_no_reason")
    tasks.register(with_before, namespace="with_before")

    mocker.patch("quickie.app._tasks", tasks)
    mocker.patch("quickie.app.load_tasks")

    with raises(SystemExit) as exc_info:
        _cli.main(["-v", "stop"])
    assert exc_info.value.code == 10
    out, err = capsys.readouterr()
    assert "Stopping: My message" in err

    with raises(SystemExit) as exc_info:
        _cli.main(["-v", "stop_no_reason"])
    assert exc_info.value.code == 5
    out, err = capsys.readouterr()
    assert "Stopping because" in err

    with raises(SystemExit) as exc_info:
        _cli.main(["-v", "with_before"])
    assert exc_info.value.code == 10
    out, err = capsys.readouterr()
    assert "Stopping: My message" in err


def test_cli_uses_last_loaded_task_on_alias_collision(mocker):
    result = []

    @task(name="first", aliases=["shared"])
    def first_task():
        result.append("first")

    @task(name="shared")
    def second_task():
        result.append("second")

    tasks = RootNamespace()
    tasks.register(first_task, namespace="first")
    tasks.register(first_task, namespace="shared")
    tasks.register(second_task, namespace="shared")

    mocker.patch("quickie.app._tasks", tasks)
    mocker.patch("quickie.app.load_tasks")

    with raises(SystemExit) as exc_info:
        _cli.main(["shared"])
    assert exc_info.value.code == 0
    assert result == ["second"]


@mark.integration
def test_namespaced_task_not_found_message(capsys):
    with raises(SystemExit) as exc_info:
        _cli.main(["nested:missing"])
    assert exc_info.value.code == 1

    out, err = capsys.readouterr()
    assert not out
    assert "Task 'nested:missing' not found" in err


def test_cli_exits_with_subprocess_return_code(capsys, mocker):
    @task
    def failing_task():
        raise SubprocessExitCodeError(
            task_name="failing-task",
            return_code=7,
            command="myprogram --fail",
            expected_exit_codes=(0,),
        )

    tasks = RootNamespace()
    tasks.register(failing_task, namespace="failing-task")

    mocker.patch("quickie.app._tasks", tasks)
    mocker.patch("quickie.app.load_tasks")

    with raises(SystemExit) as exc_info:
        _cli.main(["failing-task"])
    assert exc_info.value.code == 7

    out, err = capsys.readouterr()
    assert not out
    assert "Task 'failing-task' failed with exit code 7" in err


class TestAutocompletion:
    @pytest.fixture(autouse=True)
    def add_env(self):
        set_keys = {}

        def fn(key, value):
            if key in os.environ:
                set_keys[key] = os.environ[key]
            else:
                set_keys[key] = None
            os.environ[key] = value

        yield fn
        for key, value in set_keys.items():
            if value is None:
                os.environ.pop(key)
            else:
                os.environ[key] = value

    @mark.integration
    def test_autocompletion(self, add_env, mocker):
        add_env("_ARGCOMPLETE", "1")
        add_env("COMP_LINE", "qk test ")
        add_env("COMP_POINT", "4")
        autocomplete_mock = mocker.patch("argcomplete.autocomplete")
        with raises(SystemExit) as exc_info:
            _cli.main([])
        assert exc_info.value.code == 0
        autocomplete_mock.assert_called_once()
        # check the args passed to the autocomplete function
        args, _ = autocomplete_mock.call_args
        assert args[0].description
        assert args[0].description == AppArgumentParser().description

    @mark.integration
    def test_task_autocompletion(self, add_env, mocker):
        add_env("_ARGCOMPLETE", "1")
        add_env("COMP_LINE", "qk hello ")
        add_env("COMP_POINT", "10")
        autocomplete_mock = mocker.patch("argcomplete.autocomplete")
        with raises(SystemExit) as exc_info:
            _cli.main([])
        assert exc_info.value.code == 0
        autocomplete_mock.assert_called_once()
        # check the args passed to the autocomplete function
        args, _ = autocomplete_mock.call_args
        assert args[0].description == "Hello world task."


class TestPartitionArgs:
    def setup_method(self):
        self.parser = AppArgumentParser()

    def test_log_file_consumes_value(self):
        ns = self.parser.parse_args(["--log-file", "/tmp/log.txt", "my-task", "arg1"])
        assert ns.log_file == "/tmp/log.txt"
        assert ns.task == "my-task"
        assert ns.args == ["arg1"]

    def test_module_flag_consumes_value(self):
        ns = self.parser.parse_args(["-m", "/path/to/module", "my-task"])
        assert ns.module == "/path/to/module"
        assert ns.task == "my-task"

    def test_long_module_flag_consumes_value(self):
        ns = self.parser.parse_args(["--module", "/path/to/module", "my-task"])
        assert ns.module == "/path/to/module"
        assert ns.task == "my-task"

    def test_verbosity_flag_before_task(self):
        ns = self.parser.parse_args(["-v", "my-task", "arg1"])
        assert ns.verbosity == 1
        assert ns.task == "my-task"
        assert ns.args == ["arg1"]

    def test_task_only(self):
        ns = self.parser.parse_args(["my-task"])
        assert ns.task == "my-task"
        assert ns.args == []

    def test_no_task_only_flags(self):
        ns = self.parser.parse_args(["-v"])
        assert ns.task is None
        assert ns.args == []

    def test_task_with_multiple_args(self):
        ns = self.parser.parse_args(["my-task", "arg1", "arg2", "--extra"])
        assert ns.task == "my-task"
        assert ns.args == ["arg1", "arg2", "--extra"]

    def test_empty_args(self):
        ns = self.parser.parse_args([])
        assert ns.task is None
        assert ns.args == []

    def test_empty_string_arg_preserved_for_completion(self):
        # argcomplete passes [""] when the user typed "qk " (trailing space).
        # partition_args must not drop it (empty string is falsy but not None).
        ns = self.parser.parse_args([""])
        assert ns.task == ""
        assert ns.args == []


def test_unrecognized_args(capsys):
    with raises(SystemExit) as exc_info:
        _cli.main(["--unknown-quickie-flag"])
    assert exc_info.value.code == 2
    _, err = capsys.readouterr()
    assert "unrecognized arguments" in err


def test_skip_at_top_level(capsys, mocker):
    def before_raises_skip():
        raise Skip("test skip message")

    @task(before=[before_raises_skip])
    def skipped_task():
        pass

    tasks_ns = RootNamespace()
    tasks_ns.register(skipped_task, namespace="skipped-task")
    mocker.patch("quickie.app._tasks", tasks_ns)
    mocker.patch("quickie.app.load_tasks")

    _cli.main(["-v", "skipped-task"])
    _, err = capsys.readouterr()
    assert "Skipping" in err


def test_skip_at_top_level_no_message(capsys, mocker):
    def before_raises_skip():
        raise Skip()

    @task(before=[before_raises_skip])
    def skipped_task2():
        pass

    tasks_ns = RootNamespace()
    tasks_ns.register(skipped_task2, namespace="skipped-task2")
    mocker.patch("quickie.app._tasks", tasks_ns)
    mocker.patch("quickie.app.load_tasks")

    _cli.main(["-v", "skipped-task2"])
    _, err = capsys.readouterr()
    assert "Skipping because" in err


def test_keyboard_interrupt(mocker, capsys):
    mocker.patch("quickie._cli.Main.__call__", side_effect=KeyboardInterrupt)

    with raises(SystemExit) as exc_info:
        _cli.main([])
    assert exc_info.value.code == 1
    out, _ = capsys.readouterr()
    assert "KeyboardInterrupt" in out


@mark.integration
def test_init_flag(capsys, tmp_path):
    with raises(SystemExit) as exc_info:
        _cli.main(["--init", str(tmp_path)])
    assert exc_info.value.code == 0
    assert (tmp_path / "_qk").exists()
    assert (tmp_path / "_qk" / "__init__.py").exists()


@mark.integration
def test_init_flag_already_initialized(capsys, tmp_path):
    existing_dir = tmp_path / "_qk"
    existing_dir.mkdir()
    with raises(SystemExit) as exc_info:
        _cli.main(["--init", str(tmp_path)])
    assert exc_info.value.code == 0
    out, _ = capsys.readouterr()
    assert "already initialized" in out


def test_module_flag(mocker, capsys):
    @task
    def module_hello():
        pass

    tasks_ns = RootNamespace()
    tasks_ns.register(module_hello, namespace="module-hello")
    mocker.patch("quickie.app._tasks", tasks_ns)
    mocker.patch("quickie.app.load_tasks")
    set_project_path_mock = mocker.patch.object(quickie_app, "set_project_path")

    with raises(SystemExit):
        _cli.main(["--module", "tests/_qk_test", "module-hello"])

    set_project_path_mock.assert_called_once_with("tests/_qk_test")
