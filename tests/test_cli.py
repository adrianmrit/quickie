import re
import subprocess
import sys

from _pytest.capture import CaptureFixture
from pytest import mark, raises

from task_mom import cli

PYTHON_PATH = sys.executable
BIN_FOLDER = sys.prefix + "/bin"
BIN_LOCATION = BIN_FOLDER + "/mom"


@mark.integration
@mark.parametrize(
    "argv",
    [
        [BIN_LOCATION, "-h"],
        [PYTHON_PATH, "-m", "task_mom", "-h", "hello"],
        [PYTHON_PATH, "-m", "task_mom", "hello"],
        [PYTHON_PATH, "-m", "task_mom", "-h"],
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
def test_help(argv, capsys: CaptureFixture):
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
        ["-h", "hello"],
        ["--help", "hello"],
    ],
)
def test_task_help(argv, capsys: CaptureFixture):
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
        ["-h", "hello", "arg1"],
        ["--help", "hello", "arg1"],
    ],
)
def test_task_help_with_args(argv, capsys: CaptureFixture):
    with raises(SystemExit) as exc_info:
        cli.main(argv)
    assert exc_info.value.code == 2

    out, err = capsys.readouterr()
    assert "error: -h/--help only accepts one task name" in out
    assert not err


@mark.integration
@mark.parametrize(
    "argv",
    [
        ["-V"],
        ["--version"],
    ],
)
def test_version(argv, capsys: CaptureFixture):
    with raises(SystemExit) as exc_info:
        cli.main(argv)
    assert exc_info.value.code == 0

    out, err = capsys.readouterr()
    assert re.match(r"\d+\.\d+\..*", out)
    assert not err


@mark.integration
def test_default(capsys: CaptureFixture):
    with raises(SystemExit) as exc_info:
        cli.main([])
    assert exc_info.value.code == 0
    out, err = capsys.readouterr()
    assert "[-h [TASK] | -V] [TASK] [ARGS ...]" in out
    assert not err


@mark.integration
def test_fails_find_paths():
    with raises(FileNotFoundError, match="nonexistent.py"):
        cli.main(["-h", "hello"], task_paths=["nonexistent.py"])


@mark.integration
def test_fails_find_task():
    with raises(ValueError, match="Task 'nonexistent' not found"):
        cli.main(["nonexistent"])
