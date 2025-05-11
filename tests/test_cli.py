import os
import re
import subprocess
import sys

import pytest
from pytest import mark, raises

from quickie import _cli
from quickie._argparser import AppArgumentParser
from quickie._namespace import RootNamespace
from quickie.errors import Stop
from quickie.factories import task

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
    assert "other_task" in out, f"out: {out}, err: {err}"
    assert "cls_holder:hello" in out, f"out: {out}, err: {err}"
    assert "dict:task:hello" in out, f"out: {out}, err: {err}"
    assert "dict:task:other_ta" in out, f"out: {out}, err: {err}"
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
        assert args[0].description == AppArgumentParser(None).description

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
