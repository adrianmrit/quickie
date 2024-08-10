import os
import re
import subprocess
import sys

import pytest
from pytest import mark, raises

from quickie import cli
from quickie.argparser import ArgumentsParser

PYTHON_PATH = sys.executable
BIN_FOLDER = os.path.join(sys.prefix, "bin")
BIN_LOCATION = os.path.join(BIN_FOLDER, "qck")


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
        cli.main(argv)
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
        cli.main(argv)
    assert exc_info.value.code == 0

    out, err = capsys.readouterr()
    assert "Hello world task." in out
    assert not err


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
        cli.main(argv)
    assert exc_info.value.code == 0

    out, err = capsys.readouterr()
    assert re.match(r"\d+\.\d+\..*", out)
    assert not err


@mark.integration
def test_default(capsys):
    with raises(SystemExit) as exc_info:
        cli.main([])
    assert exc_info.value.code == 0
    out, err = capsys.readouterr()
    assert "[-h] [-V] [-l] [-m MODULE | -g | --autocomplete {bash,zsh}]" in out
    assert not err


@mark.integration
def test_fails_find_task():
    with raises(cli.QuickieError, match="Task 'nonexistent' not found"):
        cli.main(["nonexistent"], raise_error=True)


@mark.integration
def test_main_no_args(capsys):
    with raises(SystemExit) as exc_info:
        cli.main()
    # Depending how we run it we might get a different exit code
    assert exc_info.value.code in (0, 2)
    out, err = capsys.readouterr()
    out = out + err
    assert "[-h] [-V] [-l] [-m MODULE | -g | --autocomplete {bash,zsh}]" in out


@mark.integration
def test_task_not_found(capsys):
    with raises(SystemExit) as exc_info:
        cli.main(["nonexistent"])
    assert exc_info.value.code == 1
    out, err = capsys.readouterr()
    assert "Task 'nonexistent' not found" in out


@mark.integration
def test_list(capsys):
    with raises(SystemExit) as exc_info:
        cli.main(["-l"])
    assert exc_info.value.code == 0
    out, err = capsys.readouterr()
    assert out == (
        "Available tasks:\n"
        "├── hello\n"
        "│     Hello world task.\n"
        "└── nested\n"
        "    └── other\n"
        "          Other task.\n"
    )


@mark.integration
def test_suggest_autocompletion_bash(capsys):
    with raises(SystemExit) as exc_info:
        cli.main(["--autocomplete", "bash"])
    assert exc_info.value.code == 0
    out, err = capsys.readouterr()
    assert 'eval "$(register-python-argcomplete qck)"' in out


@mark.integration
def test_suggest_autocompletion_zsh(capsys):
    with raises(SystemExit) as exc_info:
        cli.main(["--autocomplete", "zsh"])
    assert exc_info.value.code == 0
    out, err = capsys.readouterr()
    assert 'eval "$(register-python-argcomplete qck)"' in out


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
        add_env("COMP_LINE", "qck test ")
        add_env("COMP_POINT", "4")
        autocomplete_mock = mocker.patch("argcomplete.autocomplete")
        with raises(SystemExit) as exc_info:
            cli.main([])
        assert exc_info.value.code == 0
        autocomplete_mock.assert_called_once()
        # check the args passed to the autocomplete function
        args, _ = autocomplete_mock.call_args
        assert args[0].description
        assert args[0].description == ArgumentsParser(None).description

    @mark.integration
    def test_task_autocompletion(self, add_env, mocker):
        add_env("_ARGCOMPLETE", "1")
        add_env("COMP_LINE", "qck hello ")
        add_env("COMP_POINT", "10")
        autocomplete_mock = mocker.patch("argcomplete.autocomplete")
        with raises(SystemExit) as exc_info:
            cli.main([])
        assert exc_info.value.code == 0
        autocomplete_mock.assert_called_once()
        # check the args passed to the autocomplete function
        args, _ = autocomplete_mock.call_args
        assert args[0].description == "Hello world task."
