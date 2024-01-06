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
    assert "show this help message and exit" in out
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
    cli.main([])
    out, err = capsys.readouterr()
    assert not out
    assert not err


@mark.integration
@mark.parametrize(
    "argv",
    [
        ["-p"],
        ["--print"],
    ],
)
def test_print(argv, capsys: CaptureFixture):
    cli.main(argv)
    out, err = capsys.readouterr()
    assert "Hello world!" in out
    assert not err
