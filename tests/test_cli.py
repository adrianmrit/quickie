import os
import re
import json
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
        [PYTHON_PATH, "-m", "quickie", "-h", "examples:hello"],
        [PYTHON_PATH, "-m", "quickie", "examples:hello"],
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
    assert "Hello" in out
    assert "world" in out
    assert "task." in out


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
    assert "\x1b[" not in out


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
    assert exc_info.value.code == 127
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
    assert "Hello" in out
    assert "world" in out
    assert "task." in out

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
    assert exc_info.value.code == 127

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


class TestListTasks:
    """Tests for list_tasks functionality."""

    def test_list_tasks_outputs_table(self, capsys, mocker):
        """Test that list_tasks outputs a formatted table."""

        @task
        def sample_task():
            """Sample task for testing."""
            pass

        tasks_ns = RootNamespace()
        tasks_ns.register(sample_task, namespace="sample-task")
        mocker.patch("quickie.app._tasks", tasks_ns)
        mocker.patch("quickie.app.load_tasks")

        main_obj = _cli.Main(argv=["--list"])
        main_obj.list_tasks()

        out, _ = capsys.readouterr()
        assert "Available tasks" in out
        assert "sample-task" in out

    def test_list_tasks_with_aliases(self, capsys, mocker):
        """Test list_tasks shows aliases."""

        @task(aliases=["alias1", "alias2"])
        def aliased_task():
            """Task with aliases."""
            pass

        tasks_ns = RootNamespace()
        # Register the task under multiple names
        tasks_ns.register(aliased_task, namespace="aliased-task")
        tasks_ns.register(aliased_task, namespace="alias1")
        tasks_ns.register(aliased_task, namespace="alias2")
        mocker.patch("quickie.app._tasks", tasks_ns)
        mocker.patch("quickie.app.load_tasks")

        main_obj = _cli.Main(argv=["--list"])
        main_obj.list_tasks()

        out, _ = capsys.readouterr()
        # Aliases should be shown in the Aliases column
        assert "alias1" in out or "alias2" in out

    def test_list_tasks_uses_invocation_paths_and_filter(self, capsys, mocker):
        @task(aliases=["check"])
        def test_task():
            pass

        tasks_ns = RootNamespace()
        tasks_ns.register(test_task, namespace="ci:test-task")
        tasks_ns.register(test_task, namespace="ci:check")
        mocker.patch("quickie.app._tasks", tasks_ns)

        main_obj = _cli.Main(argv=["--list", "--list-filter", "CHECK"])
        main_obj.list_tasks(main_obj.namespace.list_filter)

        out, _ = capsys.readouterr()
        assert "test-task" in out
        assert "ci:check" in out
        assert "ci:test-task" in out
        assert "│" in out

    def test_list_filter_without_value_lists_all_tasks(self, capsys, mocker):
        @task
        def sample_task():
            pass

        tasks_ns = RootNamespace()
        tasks_ns.register(sample_task, namespace="sample-task")
        mocker.patch("quickie.app._tasks", tasks_ns)

        main_obj = _cli.Main(argv=["--list", "--list-filter"])
        main_obj.list_tasks(main_obj.namespace.list_filter)

        assert "sample-task" in capsys.readouterr().out


class TestListTasksJson:
    """Tests for list_tasks_json functionality."""

    def test_list_tasks_json_outputs_json(self, capsys, mocker):
        """Test that list_tasks_json outputs valid JSON."""

        @task
        def json_task():
            """JSON task for testing."""
            pass

        tasks_ns = RootNamespace()
        tasks_ns.register(json_task, namespace="json-task")
        mocker.patch("quickie.app._tasks", tasks_ns)
        mocker.patch("quickie.app.load_tasks")

        main_obj = _cli.Main(argv=["--list-json"])
        main_obj.list_tasks_json()

        out, _ = capsys.readouterr()
        import json

        data = json.loads(out)
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["name"] == "json-task"

    def test_list_tasks_json_uses_invocable_path_and_aliases(self, capsys, mocker):
        @task(aliases=["verify"])
        def check():
            pass

        tasks_ns = RootNamespace()
        tasks_ns.register(check, namespace="ci:check")
        tasks_ns.register(check, namespace="ci:verify")
        mocker.patch("quickie.app._tasks", tasks_ns)

        main_obj = _cli.Main(argv=["--list-json"])
        main_obj.list_tasks_json()

        data = json.loads(capsys.readouterr().out)
        assert data[0]["name"] == "ci:check"
        assert data[0]["aliases"] == ["ci:verify"]

    def test_list_tasks_json_prefers_direct_path(self, capsys, mocker):
        @task
        def check():
            pass

        tasks_ns = RootNamespace()
        tasks_ns.register(check, namespace="check")
        tasks_ns.register(check, namespace="ci:check")
        mocker.patch("quickie.app._tasks", tasks_ns)

        main_obj = _cli.Main(argv=["--list-json"])
        main_obj.list_tasks_json()

        data = json.loads(capsys.readouterr().out)
        assert data[0]["name"] == "check"
        assert data[0]["aliases"] == ["ci:check"]

    def test_list_tasks_json_uses_declared_name_not_sort_order(self, capsys, mocker):
        @task(name="b", aliases=["a"])
        def task_b():
            pass

        tasks_ns = RootNamespace()
        tasks_ns.register(task_b, namespace="n:a")
        tasks_ns.register(task_b, namespace="n:b")
        mocker.patch("quickie.app._tasks", tasks_ns)

        main_obj = _cli.Main(argv=["--list-json"])
        main_obj.list_tasks_json()

        data = json.loads(capsys.readouterr().out)
        assert data[0]["name"] == "n:b"
        assert data[0]["aliases"] == ["n:a"]

    def test_list_tasks_json_falls_back_when_no_canonical_path(self, capsys, mocker):
        @task(name="declared")
        def task_obj():
            pass

        tasks_ns = RootNamespace()
        tasks_ns.register(task_obj, namespace="n:z")
        tasks_ns.register(task_obj, namespace="n:a")
        mocker.patch("quickie.app._tasks", tasks_ns)

        main_obj = _cli.Main(argv=["--list-json"])
        main_obj.list_tasks_json()

        data = json.loads(capsys.readouterr().out)
        assert data[0]["name"] == "n:a"
        assert data[0]["aliases"] == ["n:z"]


class TestSuggestAutocompletion:
    """Tests for autocompletion suggestions."""

    def test_suggest_autocompletion_bash(self, capsys, mocker):
        """Test bash autocompletion suggestion."""
        mocker.patch("sys.argv", ["qk"])

        main_obj = _cli.Main(argv=[])
        main_obj.suggest_autocompletion_bash()

        out, _ = capsys.readouterr()
        assert "bashrc" in out or "bash_profile" in out
        assert "register-python-argcomplete" in out

    def test_suggest_autocompletion_zsh(self, capsys, mocker):
        """Test zsh autocompletion suggestion."""
        mocker.patch("sys.argv", ["qk"])

        main_obj = _cli.Main(argv=[])
        main_obj.suggest_autocompletion_zsh()

        out, _ = capsys.readouterr()
        assert "zshrc" in out
        assert "register-python-argcomplete" in out


class TestMainErrorHandling:
    """Tests for main() error handling paths."""

    def test_main_with_stop_exception(self, mocker, capsys):
        """Test main() handles Stop exception."""
        mocker.patch("quickie.app.load_tasks")
        mocker.patch("quickie.app.set_project_path")
        mocker.patch("quickie.app.set_use_global")
        mocker.patch("quickie.app.set_log_file")

        @task
        def stop_task():
            raise Stop("Test stop")

        tasks_ns = RootNamespace()
        tasks_ns.register(stop_task, namespace="stop-task")
        mocker.patch("quickie.app._tasks", tasks_ns)

        with raises(SystemExit) as exc_info:
            _cli.main(["--global", "stop-task"])
        assert exc_info.value.code == 0

    def test_main_with_skip_exception(self, mocker, capsys):
        """Test main() handles Skip exception."""
        mocker.patch("quickie.app.load_tasks")
        mocker.patch("quickie.app.set_project_path")
        mocker.patch("quickie.app.set_use_global")
        mocker.patch("quickie.app.set_log_file")

        @task
        def skip_task():
            raise Skip("Test skip")

        tasks_ns = RootNamespace()
        tasks_ns.register(skip_task, namespace="skip-task")
        mocker.patch("quickie.app._tasks", tasks_ns)

        with raises(SystemExit) as exc_info:
            _cli.main(["--global", "skip-task"])
        assert exc_info.value.code == 0

    def test_main_with_quickie_error_raise(self, mocker):
        """Test main() raises QuickieError when raise_error=True."""
        mocker.patch("quickie.app.load_tasks")
        mocker.patch("quickie.app.set_project_path")
        mocker.patch("quickie.app.set_use_global")
        mocker.patch("quickie.app.set_log_file")

        from quickie.errors import QuickieError

        @task
        def error_task():
            raise QuickieError("Test error", exit_code=1)

        tasks_ns = RootNamespace()
        tasks_ns.register(error_task, namespace="error-task")
        mocker.patch("quickie.app._tasks", tasks_ns)

        with raises(QuickieError):
            _cli.main(["--global", "error-task"], raise_error=True)

    def test_main_with_global_flag(self, mocker):
        """Test main() with --global flag bypasses launcher."""
        mocker.patch("quickie.app.load_tasks")
        mocker.patch("quickie.app.set_project_path")
        mocker.patch("quickie.app.set_use_global")
        mocker.patch("quickie.app.set_log_file")

        @task
        def global_task():
            pass

        tasks_ns = RootNamespace()
        tasks_ns.register(global_task, namespace="global-task")
        mocker.patch("quickie.app._tasks", tasks_ns)

        with raises(SystemExit):
            _cli.main(["--global", "global-task"])

    def test_main_with_init_flag(self, capsys, tmp_path):
        """Test main() with --init flag."""
        with raises(SystemExit) as exc_info:
            _cli.main(["--init", str(tmp_path)])
        assert exc_info.value.code == 0
        assert (tmp_path / "_qk").exists()

    def test_main_with_list_flag(self, mocker, capsys):
        """Test main() with --list flag."""
        mocker.patch("quickie.app.load_tasks")
        mocker.patch("quickie.app.set_project_path")
        mocker.patch("quickie.app.set_use_global")
        mocker.patch("quickie.app.set_log_file")

        @task
        def list_task():
            """List task."""
            pass

        tasks_ns = RootNamespace()
        tasks_ns.register(list_task, namespace="list-task")
        mocker.patch("quickie.app._tasks", tasks_ns)

        with raises(SystemExit):
            _cli.main(["--global", "--list"])

        out, _ = capsys.readouterr()
        assert "Available tasks" in out


@mark.integration
class TestWatchTask:
    """Tests for the watch_task method."""

    def _register_task(self, mocker, task_obj, name="watch-me"):
        """Helper to register a task in the namespace."""
        ns = RootNamespace()
        ns.register(task_obj, namespace=name)
        mocker.patch("quickie.app._tasks", ns)
        mocker.patch("quickie.app.load_tasks")

    def test_watch_task_runs_task_once(self, mocker, capsys):
        """watch_task runs the task immediately on start."""
        mock_watcher_class = mocker.patch("quickie._watcher.FileWatcher")
        instance = mock_watcher_class.return_value
        instance.wait_for_changes.side_effect = KeyboardInterrupt

        @task
        def watch_me():
            print("task ran")

        self._register_task(mocker, watch_me)

        with raises(SystemExit):
            _cli.main(["--watch", "watch-me"])

        out, _ = capsys.readouterr()
        assert "Watching for changes" in out
        assert "task ran" in out

    def test_watch_task_starts_watcher_after_initial_run(self, mocker):
        """Initial task changes are not treated as a watch trigger."""
        mock_watcher_class = mocker.patch("quickie._watcher.FileWatcher")
        instance = mock_watcher_class.return_value
        instance.wait_for_changes.side_effect = KeyboardInterrupt
        events = []
        instance.start.side_effect = lambda: events.append("start")

        @task
        def watch_me():
            events.append("task")

        self._register_task(mocker, watch_me)

        with raises(SystemExit):
            _cli.main(["--watch", "watch-me"])

        assert events == ["task", "start"]

    def test_watch_task_reruns_on_changes(self, mocker, capsys):
        """watch_task re-runs when changes are detected."""
        mock_watcher_class = mocker.patch("quickie._watcher.FileWatcher")
        instance = mock_watcher_class.return_value
        instance.wait_for_changes.side_effect = [True, KeyboardInterrupt]
        instance.changed_paths.return_value = ["src/example.py"]

        @task
        def watch_me():
            print("ran")

        self._register_task(mocker, watch_me)

        with raises(SystemExit):
            _cli.main(["--watch", "watch-me"])

        out, _ = capsys.readouterr()
        assert "Changes detected" in out
        assert "src/example.py" in out

    def test_watch_task_with_ignore_pattern(self, mocker, capsys):
        """watch_task prints ignore patterns."""
        mock_watcher_class = mocker.patch("quickie._watcher.FileWatcher")
        instance = mock_watcher_class.return_value
        instance.wait_for_changes.side_effect = KeyboardInterrupt

        @task
        def watch_me():
            pass

        self._register_task(mocker, watch_me)

        with raises(SystemExit):
            _cli.main(
                [
                    "--watch",
                    "--watch-ignore-patterns",
                    "build/",
                    "watch-me",
                ]
            )

        out, _ = capsys.readouterr()
        assert "build/" in out

    def test_watch_task_custom_debounce(self, mocker):
        """watch_task passes debounce to FileWatcher."""
        mock_watcher_class = mocker.patch("quickie._watcher.FileWatcher")
        instance = mock_watcher_class.return_value
        instance.wait_for_changes.side_effect = KeyboardInterrupt

        @task
        def watch_me():
            pass

        self._register_task(mocker, watch_me)

        with raises(SystemExit):
            _cli.main(
                [
                    "--watch",
                    "--watch-debounce",
                    "2.0",
                    "watch-me",
                ]
            )

        _, kwargs = mock_watcher_class.call_args
        assert kwargs["debounce"] == 2.0

    def test_watch_task_uses_task_defaults(self, mocker):
        """watch_task falls back to task-defined watch_paths."""
        mock_watcher_class = mocker.patch("quickie._watcher.FileWatcher")
        instance = mock_watcher_class.return_value
        instance.wait_for_changes.side_effect = KeyboardInterrupt

        @task(watch_paths=["src/"], watch_ignore_patterns=["tests/"])
        def watch_me():
            pass

        self._register_task(mocker, watch_me)

        with raises(SystemExit):
            _cli.main(["--watch", "watch-me"])

        _, kwargs = mock_watcher_class.call_args
        assert kwargs["watch_paths"] == ["src/"]
        assert "tests/" in kwargs["ignore_patterns"]

    def test_watch_task_cli_overrides_task_defaults(self, mocker):
        """CLI args override task-defined defaults."""
        mock_watcher_class = mocker.patch("quickie._watcher.FileWatcher")
        instance = mock_watcher_class.return_value
        instance.wait_for_changes.side_effect = KeyboardInterrupt

        @task(watch_paths=["src/"])
        def watch_me():
            pass

        self._register_task(mocker, watch_me)

        with raises(SystemExit):
            _cli.main(
                [
                    "--watch",
                    "--watch-paths",
                    "lib/",
                    "watch-me",
                ]
            )

        _, kwargs = mock_watcher_class.call_args
        assert kwargs["watch_paths"] == ["lib/"]

    def test_watch_task_splits_cli_patterns_and_passes_recursive(self, mocker):
        """CLI watch patterns use semicolons and recursive reaches watcher."""
        mock_watcher_class = mocker.patch("quickie._watcher.FileWatcher")
        instance = mock_watcher_class.return_value
        instance.wait_for_changes.side_effect = KeyboardInterrupt

        @task
        def watch_me():
            pass

        self._register_task(mocker, watch_me)

        with raises(SystemExit):
            _cli.main(
                [
                    "--watch",
                    "--watch-paths",
                    "src",
                    "--watch-patterns",
                    "*.py;*.pyi",
                    "--watch-recursive",
                    "watch-me",
                ]
            )

        _, kwargs = mock_watcher_class.call_args
        assert kwargs["watch_paths"] == ["src"]
        assert kwargs["patterns"] == ["*.py", "*.pyi"]
        assert kwargs["recursive"] is True

    def test_watch_task_stop_message(self, mocker, capsys):
        """Ctrl+C prints watching stopped message."""
        mock_watcher_class = mocker.patch("quickie._watcher.FileWatcher")
        instance = mock_watcher_class.return_value
        instance.wait_for_changes.side_effect = KeyboardInterrupt

        @task
        def watch_me():
            pass

        self._register_task(mocker, watch_me)

        with raises(SystemExit):
            _cli.main(["--watch", "watch-me"])

        out, _ = capsys.readouterr()
        assert "Watching stopped" in out

    def test_watch_without_task_exits_with_error(self, capsys):
        """--watch without a task exits with error."""
        with raises(SystemExit) as exc_info:
            _cli.main(["--watch"])
        assert exc_info.value.code == 1

    def test_watch_task_default_watch_paths(self, mocker):
        """watch_task defaults to ['.'] when no paths given."""
        mock_watcher_class = mocker.patch("quickie._watcher.FileWatcher")
        instance = mock_watcher_class.return_value
        instance.wait_for_changes.side_effect = KeyboardInterrupt

        @task
        def watch_me():
            pass

        self._register_task(mocker, watch_me)

        with raises(SystemExit):
            _cli.main(["--watch", "watch-me"])

        _, kwargs = mock_watcher_class.call_args
        assert kwargs["watch_paths"] == ["."]

    def test_watch_task_stops_watcher_on_exit(self, mocker):
        """watch_task calls watcher.stop() in finally block."""
        mock_watcher_class = mocker.patch("quickie._watcher.FileWatcher")
        instance = mock_watcher_class.return_value
        instance.wait_for_changes.side_effect = KeyboardInterrupt

        @task
        def watch_me():
            pass

        self._register_task(mocker, watch_me)

        with raises(SystemExit):
            _cli.main(["--watch", "watch-me"])

        instance.stop.assert_called_once()
