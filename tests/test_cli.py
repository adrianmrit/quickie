import os
import re
import subprocess
import sys

from pytest import mark, raises

from task_mom import cli

PYTHON_PATH = sys.executable
BIN_FOLDER = os.path.join(sys.prefix, "bin")
BIN_LOCATION = os.path.join(BIN_FOLDER, "mom")


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
    assert "[-h] [-V] [-l] [-m MODULE | -g] [task] [args ...]" in out
    assert not err


@mark.integration
def test_fails_find_task():
    with raises(cli.MomError, match="Task 'nonexistent' not found"):
        cli.main(["nonexistent"], raise_error=True)


@mark.integration
def test_main_no_args(capsys):
    with raises(SystemExit) as exc_info:
        cli.main()
    # Depending how we run it we might get a different exit code
    assert exc_info.value.code in (0, 2)
    out, err = capsys.readouterr()
    out = out + err
    assert "[-h] [-V] [-l] [-m MODULE | -g] [task] [args ...]" in out
