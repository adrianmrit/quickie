import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from quickie import _cli


PROJECT = Path(__file__).resolve().parents[1] / "_qk"
TASK = "examples:arguments-example"
DEFAULT_ARGUMENTS = {
    "target": "target",
    "name": "world",
    "count": 1,
    "tags": [],
    "loud": False,
    "mode": "safe",
    "paths": None,
    "extra": [],
}
ARGUMENT_CASES = [
    pytest.param(["target"], {}, id="defaults"),
    pytest.param(
        ["target", "--name", "alice", "--count", "3"],
        {"name": "alice", "count": 3},
        id="long-options",
    ),
    pytest.param(
        ["--name", "alice", "target", "-c", "-2", "--loud"],
        {"name": "alice", "count": -2, "loud": True},
        id="options-around-positional",
    ),
    pytest.param(
        ["target", "-nalice", "-c2"],
        {"name": "alice", "count": 2},
        id="attached-short-values",
    ),
    pytest.param(
        ["target", "--name=alice", "--count=2", "--mode=fast"],
        {"name": "alice", "count": 2, "mode": "fast"},
        id="equals-values",
    ),
    pytest.param(
        ["target", "--name", "alice", "--name", "bob", "--tag", "one", "--tag", "two"],
        {"name": "bob", "tags": ["one", "two"]},
        id="repeated-options",
    ),
    pytest.param(
        ["target", "first", "--foreign", "value", "last"],
        {"extra": ["first", "--foreign", "value", "last"]},
        id="unknown-option-and-positionals",
    ),
    pytest.param(
        ["target", "first", "--name", "alice", "last"],
        {"name": "alice", "extra": ["first", "last"]},
        id="known-option-between-extra-arguments",
    ),
    pytest.param(
        ["target", "--paths", "task-path", "-v", "-g", ":list"],
        {"paths": "task-path", "extra": ["-v", "-g", ":list"]},
        id="quickie-and-watch-option-collisions",
    ),
    pytest.param(
        ["target", "--", "--name", "alice", "--count", "2", "--help"],
        {"extra": ["--name", "alice", "--count", "2", "--help"]},
        id="separator-stops-task-option-parsing",
    ),
    pytest.param(
        ["target", "--", "--", "last"],
        {"extra": ["--", "last"]},
        id="only-first-separator-removed",
    ),
    pytest.param(
        ["target", "first", "--", "--name", "alice"],
        {"extra": ["first", "--name", "alice"]},
        id="separator-after-extra-positional",
    ),
    pytest.param(
        ["--", "target", "--", "last"],
        {"extra": ["--", "last"]},
        id="separator-before-positional",
    ),
    pytest.param(
        ["--", "--", "last"],
        {"target": "--", "extra": ["last"]},
        id="literal-separator-as-positional",
    ),
    pytest.param(
        ["target", "--name", "Alice Smith", "", "two words", "a;b", "$(literal)"],
        {"name": "Alice Smith", "extra": ["", "two words", "a;b", "$(literal)"]},
        id="literal-extra-values",
    ),
    pytest.param(
        ["target", "--foreign=value", "--name", ""],
        {"name": "", "extra": ["--foreign=value"]},
        id="empty-option-value",
    ),
]
INVALID_CASES = [
    pytest.param(TASK, [], "required: target", id="missing-positional"),
    pytest.param(
        TASK, ["target", "--name"], "expected one argument", id="missing-value"
    ),
    pytest.param(
        TASK, ["target", "--count", "abc"], "invalid int value", id="invalid-integer"
    ),
    pytest.param(
        TASK, ["target", "--mode", "invalid"], "invalid choice", id="invalid-choice"
    ),
    pytest.param(
        "examples:hello", [], "required: --name", id="missing-required-option"
    ),
    pytest.param(
        "examples:hello",
        ["--name", "alice", "--foreign", "value"],
        "unrecognized arguments",
        id="strict-task-rejects-unknown-option",
    ),
    pytest.param(
        "examples:hello",
        ["--name", "alice", "extra"],
        "unrecognized arguments",
        id="strict-task-rejects-extra-positional",
    ),
]
SUBPROCESS_TASKS = [
    "examples:extra-command-example",
    "examples:extra-script-example",
]
SUBPROCESS_CASES = [
    ([], {"name": "world", "extra": []}),
    (
        ["--name", "alice", "--foreign", "value", "last"],
        {"name": "alice", "extra": ["--foreign", "value", "last"]},
    ),
    (
        ["--", "--name", "alice", "--", "--help"],
        {"name": "world", "extra": ["--name", "alice", "--", "--help"]},
    ),
    (
        ["-n", "Alice Smith", "", "two words", "a;b", "$(literal)", "it's literal"],
        {
            "name": "Alice Smith",
            "extra": ["", "two words", "a;b", "$(literal)", "it's literal"],
        },
    ),
]


def run_example(command, task_name, args):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "quickie",
            "-m",
            str(PROJECT),
            *command,
            task_name,
            *args,
        ],
        env=dict(os.environ, QK_LAUNCHER_RUNNING="true"),
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.integration
@pytest.mark.parametrize("command", [[], [":run"]], ids=["bare-task", "explicit-run"])
@pytest.mark.parametrize("args, overrides", ARGUMENT_CASES)
def test_task_argument_combinations(command, args, overrides):
    result = run_example(command, TASK, args)
    assert result.returncode == 0, result.stderr
    assert not result.stderr
    assert json.loads(result.stdout) == {**DEFAULT_ARGUMENTS, **overrides}


@pytest.mark.integration
@pytest.mark.parametrize("args, overrides", ARGUMENT_CASES)
def test_watch_argument_combinations(mocker, capsys, args, overrides):
    watcher_class = mocker.patch("quickie._watcher.FileWatcher")
    watcher = watcher_class.return_value
    watcher.wait_for_changes.side_effect = [True, False]
    watcher.changed_paths.return_value = ["src/example.py"]
    with pytest.raises(SystemExit) as exc_info:
        _cli.main(["-m", str(PROJECT), ":watch", "--paths", "src", TASK, *args])
    assert exc_info.value.code == 0
    out, err = capsys.readouterr()
    assert not err
    records = [json.loads(line) for line in out.splitlines() if line.startswith("{")]
    assert records == [{**DEFAULT_ARGUMENTS, **overrides}] * 2
    assert watcher_class.call_args.kwargs["watch_paths"] == ["src"]
    watcher.start.assert_called_once()
    watcher.stop.assert_called_once()


@pytest.mark.integration
@pytest.mark.parametrize("command", [[], [":run"]], ids=["bare-task", "explicit-run"])
@pytest.mark.parametrize("task_name, args, error", INVALID_CASES)
def test_invalid_task_argument_combinations(command, task_name, args, error):
    result = run_example(command, task_name, args)
    assert result.returncode == 2  # noqa: PLR2004
    assert error in result.stderr
    assert not result.stdout


@pytest.mark.integration
@pytest.mark.parametrize("task_name, args, error", INVALID_CASES)
def test_watch_rejects_invalid_task_arguments(mocker, capsys, task_name, args, error):
    watcher_class = mocker.patch("quickie._watcher.FileWatcher")
    with pytest.raises(SystemExit) as exc_info:
        _cli.main(["-m", str(PROJECT), ":watch", task_name, *args])
    assert exc_info.value.code == 2  # noqa: PLR2004
    out, err = capsys.readouterr()
    assert error in err
    assert not out
    watcher_class.assert_not_called()


@pytest.mark.integration
@pytest.mark.parametrize("command", [[], [":run"]], ids=["bare-task", "explicit-run"])
@pytest.mark.parametrize("task_name", SUBPROCESS_TASKS)
@pytest.mark.parametrize("args, expected", SUBPROCESS_CASES)
def test_subprocess_task_extra_arguments(command, task_name, args, expected):
    result = run_example(command, task_name, args)
    assert result.returncode == 0, result.stderr
    assert not result.stderr
    assert json.loads(result.stdout) == expected


@pytest.mark.integration
@pytest.mark.parametrize("task_name", SUBPROCESS_TASKS)
@pytest.mark.parametrize("args, expected", SUBPROCESS_CASES)
def test_watch_subprocess_extra_arguments(mocker, capfd, task_name, args, expected):
    watcher = mocker.patch("quickie._watcher.FileWatcher").return_value
    watcher.wait_for_changes.side_effect = [True, False]
    watcher.changed_paths.return_value = ["src/example.py"]
    with pytest.raises(SystemExit) as exc_info:
        _cli.main(["-m", str(PROJECT), ":watch", task_name, *args])
    assert exc_info.value.code == 0
    out, err = capfd.readouterr()
    assert not err
    records = [json.loads(line) for line in out.splitlines() if line.startswith("{")]
    assert records == [expected, expected]
    watcher.stop.assert_called_once()


@pytest.mark.integration
@pytest.mark.parametrize("command", [[], [":run"], [":watch"]])
@pytest.mark.parametrize("task_name", [TASK, "examples:hello", *SUBPROCESS_TASKS])
def test_task_help_without_required_arguments(command, task_name):
    result = run_example(command, task_name, ["--help"])
    assert result.returncode == 0, result.stderr
    assert "--name" in result.stdout
    assert not result.stderr
