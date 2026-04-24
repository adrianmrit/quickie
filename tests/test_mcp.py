"""Tests for quickie.mcp — the FastMCP server."""

from __future__ import annotations

import asyncio
import asyncio as _asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp import Client

from quickie.mcp import _Project, _projects, main, mcp

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_projects():
    """Save and restore _projects around each test."""
    original = dict(_projects)
    _projects.clear()
    yield
    _projects.clear()
    _projects.update(original)


def _register_project(name="default", exe=None, root=None, extra_args=None):
    """Register a _Project in _projects for testing."""
    _projects[name] = _Project(
        name=name,
        qk_exe=exe,
        project_root=root,
        extra_args=extra_args or [],
    )
    return _projects[name]


# ---------------------------------------------------------------------------
# Shared fake task data for subprocess-mock tests
# ---------------------------------------------------------------------------

_FAKE_TASK_LIST = [
    {
        "name": "hello",
        "aliases": ["hello"],
        "short_help": "Hello world task.",
        "help": "Hello world task.",
        "usage": "usage: qk hello",
        "location": "_qk/__init__.py:1",
        "args_schema": [],
    },
    {
        "name": "other-task",
        "aliases": ["other-task"],
        "short_help": "Other task.",
        "help": "Other task.",
        "usage": "usage: qk other-task",
        "location": "_qk/__init__.py:20",
        "args_schema": [],
    },
]


def _fake_list_proc(tasks=None):
    """Build a mock subprocess that returns a JSON task list."""
    proc = MagicMock()
    proc.returncode = 0
    proc.communicate = AsyncMock(
        return_value=(json.dumps(tasks or _FAKE_TASK_LIST).encode(), b"")
    )
    return proc


# ---------------------------------------------------------------------------
# list_tasks — basic
# ---------------------------------------------------------------------------


async def test_list_tasks_returns_list_of_project_entries():
    _register_project(
        "myproject",
        exe=Path("/project/.venv/bin/qk"),
        root=Path("/project"),
    )
    with patch(
        "asyncio.create_subprocess_exec", AsyncMock(return_value=_fake_list_proc())
    ):
        async with Client(mcp) as client:
            result = await client.call_tool("list_tasks", {})
    assert isinstance(result.data, list)
    assert len(result.data) == 1
    entry = result.data[0]
    assert entry["project"] == "myproject"
    assert "project_root" in entry
    assert "tasks" in entry


async def test_list_tasks_fields():
    _register_project(
        "myproject",
        exe=Path("/project/.venv/bin/qk"),
        root=Path("/project"),
    )
    with patch(
        "asyncio.create_subprocess_exec", AsyncMock(return_value=_fake_list_proc())
    ):
        async with Client(mcp) as client:
            result = await client.call_tool("list_tasks", {})
    for entry in result.data[0]["tasks"]:
        assert "name" in entry
        assert "aliases" in entry
        assert "short_help" in entry
        assert "help" in entry
        assert "usage" in entry
        assert "location" in entry
        assert "args_schema" in entry
        assert isinstance(entry["args_schema"], list)


async def test_list_tasks_no_duplicates():
    """Each unique task object must appear exactly once."""
    _register_project(
        "myproject",
        exe=Path("/project/.venv/bin/qk"),
        root=Path("/project"),
    )
    with patch(
        "asyncio.create_subprocess_exec", AsyncMock(return_value=_fake_list_proc())
    ):
        async with Client(mcp) as client:
            result = await client.call_tool("list_tasks", {})
    names = [t["name"] for t in result.data[0]["tasks"]]
    assert len(names) == len(
        set(names)
    ), "Duplicate task names found in list_tasks output"


async def test_list_tasks_contains_hello():
    _register_project(
        "myproject",
        exe=Path("/project/.venv/bin/qk"),
        root=Path("/project"),
    )
    with patch(
        "asyncio.create_subprocess_exec", AsyncMock(return_value=_fake_list_proc())
    ):
        async with Client(mcp) as client:
            result = await client.call_tool("list_tasks", {})
    names = [t["name"] for t in result.data[0]["tasks"]]
    assert "hello" in names


async def test_list_tasks_no_projects_raises():
    """list_tasks with no projects configured must raise a ToolError."""
    async with Client(mcp) as client:
        with pytest.raises(Exception, match="No projects are configured"):
            await client.call_tool("list_tasks", {})


# ---------------------------------------------------------------------------
# list_tasks — multi-project
# ---------------------------------------------------------------------------


async def test_list_tasks_multiple_projects_all_listed():
    """When project=None, all registered projects are listed."""
    _register_project("frontend", exe=Path("/fe/.venv/bin/qk"), root=Path("/fe"))
    _register_project("backend", exe=Path("/be/.venv/bin/qk"), root=Path("/be"))
    with patch(
        "asyncio.create_subprocess_exec", AsyncMock(return_value=_fake_list_proc())
    ):
        async with Client(mcp) as client:
            result = await client.call_tool("list_tasks", {})
    assert len(result.data) == 2
    projects = {e["project"] for e in result.data}
    assert projects == {"frontend", "backend"}


async def test_list_tasks_project_by_alias():
    """Passing project='alias' lists only that project."""
    _register_project("frontend", exe=Path("/fe/.venv/bin/qk"), root=Path("/fe"))
    _register_project("backend", exe=Path("/be/.venv/bin/qk"), root=Path("/be"))
    with patch(
        "asyncio.create_subprocess_exec", AsyncMock(return_value=_fake_list_proc())
    ):
        async with Client(mcp) as client:
            result = await client.call_tool("list_tasks", {"project": "frontend"})
    assert len(result.data) == 1
    assert result.data[0]["project"] == "frontend"


async def test_list_tasks_project_by_path(tmp_path):
    """Passing a path under a project root resolves to that project."""
    _register_project("myproject", exe=Path("/proj/.venv/bin/qk"), root=tmp_path)
    with patch(
        "asyncio.create_subprocess_exec", AsyncMock(return_value=_fake_list_proc())
    ):
        async with Client(mcp) as client:
            result = await client.call_tool(
                "list_tasks", {"project": str(tmp_path / "_qk")}
            )
    assert len(result.data) == 1
    assert result.data[0]["project"] == "myproject"


async def test_list_tasks_unknown_project_raises():
    """Passing an unknown project name raises a ToolError."""
    _register_project("myproject", exe=Path("/proj/.venv/bin/qk"), root=Path("/proj"))
    async with Client(mcp) as client:
        with pytest.raises(Exception, match="No project found"):
            await client.call_tool("list_tasks", {"project": "nonexistent"})


# ---------------------------------------------------------------------------
# list_tasks — subprocess delegation
# ---------------------------------------------------------------------------


async def test_list_tasks_delegates_to_local_exe():
    """When a local exe is configured, list_tasks calls it with --list-json."""
    fake_tasks = [
        {
            "name": "deploy",
            "aliases": ["deploy"],
            "short_help": "Deploy the app",
            "help": "Deploy the app to production",
            "usage": "usage: qk deploy",
            "location": "_qk/__init__.py:5",
            "args_schema": [],
        }
    ]
    captured_cmd = {}

    async def fake_exec(*cmd, **kwargs):
        captured_cmd["cmd"] = cmd
        return _fake_list_proc(fake_tasks)

    _register_project(
        "myproject", exe=Path("/project/.venv/bin/qk"), root=Path("/project")
    )
    with patch("asyncio.create_subprocess_exec", fake_exec):
        async with Client(mcp) as client:
            result = await client.call_tool("list_tasks", {})

    assert "--list-json" in captured_cmd["cmd"]
    assert captured_cmd["cmd"][0] == "/project/.venv/bin/qk"
    assert result.data[0]["project"] == "myproject"
    assert result.data[0]["project_root"] == "/project"
    for expected, actual in zip(fake_tasks, result.data[0]["tasks"]):
        for key, value in expected.items():
            assert actual[key] == value


async def test_list_tasks_local_exe_error_raises():
    """A non-zero exit from the local exe raises a ToolError."""
    proc = MagicMock()
    proc.returncode = 1
    proc.communicate = AsyncMock(return_value=(b"", b"import error"))

    _register_project(
        "myproject", exe=Path("/project/.venv/bin/qk"), root=Path("/project")
    )
    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        async with Client(mcp) as client:
            with pytest.raises(Exception):
                await client.call_tool("list_tasks", {})


async def test_list_tasks_fallback_sets_cwd(tmp_path):
    """When no local exe is found, cwd is set to the project root."""
    proc = MagicMock()
    proc.returncode = 0
    proc.communicate = AsyncMock(return_value=(b"[]", b""))
    captured_kwargs: dict = {}

    async def fake_exec(*cmd, **kwargs):
        captured_kwargs.update(kwargs)
        return proc

    _register_project(
        "myproject",
        exe=None,
        root=tmp_path,
        extra_args=["--module", str(tmp_path / "_qk")],
    )
    with patch("asyncio.create_subprocess_exec", fake_exec):
        async with Client(mcp) as client:
            await client.call_tool("list_tasks", {})

    assert captured_kwargs.get("cwd") == str(tmp_path)


async def test_list_tasks_stdin_is_devnull():
    """list_tasks subprocess must always receive DEVNULL on stdin."""
    captured_kwargs: dict = {}

    async def fake_exec(*cmd, **kwargs):
        captured_kwargs.update(kwargs)
        return _fake_list_proc()

    _register_project(
        "default", exe=Path("/project/.venv/bin/qk"), root=Path("/project")
    )
    with patch("asyncio.create_subprocess_exec", fake_exec):
        async with Client(mcp) as client:
            await client.call_tool("list_tasks", {})

    assert captured_kwargs["stdin"] == asyncio.subprocess.DEVNULL


# ---------------------------------------------------------------------------
# run_task — success cases (subprocess mocked)
# ---------------------------------------------------------------------------


def _make_async_iter(lines: list[bytes]):
    """Return an async iterator that yields the given byte strings."""

    class _AsyncIter:
        def __init__(self):
            self._it = iter(lines)

        def __aiter__(self):
            return self

        async def __anext__(self):
            try:
                return next(self._it)
            except StopIteration:
                raise StopAsyncIteration

    return _AsyncIter()


def _make_proc_mock(
    stdout_lines: list[bytes], stderr_lines: list[bytes], returncode: int = 0
):
    """Build a minimal mock of an asyncio.subprocess.Process."""
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = _make_async_iter(stdout_lines)
    proc.stderr = _make_async_iter(stderr_lines)
    proc.stdin = MagicMock()
    proc.stdin.write = MagicMock()
    proc.stdin.drain = AsyncMock()
    proc.stdin.close = MagicMock()
    proc.wait = AsyncMock(return_value=returncode)
    proc.kill = MagicMock()
    return proc


async def test_run_task_success():
    _register_project(
        "default", exe=Path("/project/.venv/bin/qk"), root=Path("/project")
    )
    proc = _make_proc_mock([b"Hello world!\n"], [], returncode=0)
    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        async with Client(mcp) as client:
            result = await client.call_tool("run_task", {"task_name": "hello"})
    assert result.data["exit_code"] == 0
    assert "Hello world!" in result.data["stdout"]


async def test_run_task_with_args():
    _register_project(
        "default", exe=Path("/project/.venv/bin/qk"), root=Path("/project")
    )
    proc = _make_proc_mock([b"arg output\n"], [], returncode=0)
    captured_cmd = {}

    async def fake_exec(*cmd, **kwargs):
        captured_cmd["cmd"] = cmd
        return proc

    with patch("asyncio.create_subprocess_exec", fake_exec):
        async with Client(mcp) as client:
            await client.call_tool(
                "run_task", {"task_name": "hello", "args": ["--flag", "val"]}
            )

    assert "--flag" in captured_cmd["cmd"]
    assert "val" in captured_cmd["cmd"]


async def test_run_task_with_stdin():
    _register_project(
        "default", exe=Path("/project/.venv/bin/qk"), root=Path("/project")
    )
    proc = _make_proc_mock([], [], returncode=0)
    kwargs_captured = {}

    async def fake_exec(*cmd, **kwargs):
        kwargs_captured.update(kwargs)
        return proc

    with patch("asyncio.create_subprocess_exec", fake_exec):
        async with Client(mcp) as client:
            await client.call_tool("run_task", {"task_name": "hello", "stdin": "y\n"})

    # When stdin is provided the subprocess must be given a PIPE, not DEVNULL.
    assert kwargs_captured["stdin"] == _asyncio.subprocess.PIPE
    proc.stdin.write.assert_called_once_with(b"y\n")
    proc.stdin.close.assert_called_once()


async def test_run_task_devnull_when_no_stdin():
    _register_project(
        "default", exe=Path("/project/.venv/bin/qk"), root=Path("/project")
    )
    proc = _make_proc_mock([], [], returncode=0)
    kwargs_captured = {}

    async def fake_exec(*cmd, **kwargs):
        kwargs_captured.update(kwargs)
        return proc

    with patch("asyncio.create_subprocess_exec", fake_exec):
        async with Client(mcp) as client:
            await client.call_tool("run_task", {"task_name": "hello"})

    assert kwargs_captured["stdin"] == _asyncio.subprocess.DEVNULL


async def test_run_task_nonzero_exit():
    _register_project(
        "default", exe=Path("/project/.venv/bin/qk"), root=Path("/project")
    )
    proc = _make_proc_mock([], [b"error msg\n"], returncode=1)
    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        async with Client(mcp) as client:
            result = await client.call_tool("run_task", {"task_name": "hello"})
    assert result.data["exit_code"] == 1
    assert "error msg" in result.data["stderr"]


async def test_run_task_launcher_env():
    _register_project(
        "default", exe=Path("/project/.venv/bin/qk"), root=Path("/project")
    )
    proc = _make_proc_mock([], [], returncode=0)
    kwargs_captured = {}

    async def fake_exec(*cmd, **kwargs):
        kwargs_captured.update(kwargs)
        return proc

    with patch("asyncio.create_subprocess_exec", fake_exec):
        async with Client(mcp) as client:
            await client.call_tool("run_task", {"task_name": "hello"})

    assert kwargs_captured["env"]["QK_LAUNCHER_RUNNING"] == "true"


# ---------------------------------------------------------------------------
# run_task — error cases
# ---------------------------------------------------------------------------


async def test_run_task_timeout():
    _register_project(
        "default", exe=Path("/project/.venv/bin/qk"), root=Path("/project")
    )

    async def hanging_exec(*cmd, **kwargs):
        proc = MagicMock()
        proc.stdout = _make_async_iter([])
        proc.stderr = _make_async_iter([])
        proc.stdin = MagicMock()
        proc.stdin.close = MagicMock()
        proc.kill = MagicMock()

        async def never_finish():
            await asyncio.sleep(999)

        proc.wait = never_finish
        return proc

    with patch("asyncio.create_subprocess_exec", hanging_exec):
        async with Client(mcp) as client:
            with pytest.raises(Exception, match="timeout"):
                await client.call_tool(
                    "run_task",
                    {"task_name": "hello", "timeout": 0.1},
                )


async def test_run_task_no_projects_raises():
    """run_task with no projects configured raises a ToolError."""
    async with Client(mcp) as client:
        with pytest.raises(Exception, match="No projects"):
            await client.call_tool("run_task", {"task_name": "hello"})


async def test_run_task_multi_project_no_project_raises():
    """run_task with multiple projects and no project raises a ToolError."""
    _register_project("frontend")
    _register_project("backend")
    async with Client(mcp) as client:
        with pytest.raises(Exception, match="Multiple projects"):
            await client.call_tool("run_task", {"task_name": "hello"})


async def test_run_task_lookup_by_alias():
    """run_task with project='alias' targets the correct project."""
    _register_project("frontend", exe=Path("/fe/.venv/bin/qk"), root=Path("/fe"))
    _register_project("backend", exe=Path("/be/.venv/bin/qk"), root=Path("/be"))
    proc = _make_proc_mock([], [], returncode=0)
    captured_cmd = {}

    async def fake_exec(*cmd, **kwargs):
        captured_cmd["cmd"] = cmd
        return proc

    with patch("asyncio.create_subprocess_exec", fake_exec):
        async with Client(mcp) as client:
            await client.call_tool(
                "run_task", {"task_name": "deploy", "project": "backend"}
            )

    assert captured_cmd["cmd"][0] == "/be/.venv/bin/qk"
    assert "deploy" in captured_cmd["cmd"]


# ---------------------------------------------------------------------------
# run_task — subprocess exe resolution
# ---------------------------------------------------------------------------


async def test_run_task_uses_local_qk_exe_when_set():
    """When a project-local qk exe is configured it should head the command."""
    _register_project(
        "default", exe=Path("/project/.venv/bin/qk"), root=Path("/project")
    )
    proc = _make_proc_mock([], [], returncode=0)
    captured_cmd = {}

    async def fake_exec(*cmd, **kwargs):
        captured_cmd["cmd"] = cmd
        return proc

    with patch("asyncio.create_subprocess_exec", fake_exec):
        async with Client(mcp) as client:
            await client.call_tool("run_task", {"task_name": "hello"})

    assert captured_cmd["cmd"][0] == "/project/.venv/bin/qk"
    assert "hello" in captured_cmd["cmd"]


async def test_run_task_falls_back_to_sys_executable_when_no_local_exe():
    """When no local exe is resolved, sys.executable -m quickie is used."""
    _register_project("default", exe=None, extra_args=[])
    proc = _make_proc_mock([], [], returncode=0)
    captured_cmd = {}

    async def fake_exec(*cmd, **kwargs):
        captured_cmd["cmd"] = cmd
        return proc

    with patch("asyncio.create_subprocess_exec", fake_exec):
        async with Client(mcp) as client:
            await client.call_tool("run_task", {"task_name": "hello"})

    assert captured_cmd["cmd"][0] == sys.executable
    assert "-m" in captured_cmd["cmd"]
    assert "quickie" in captured_cmd["cmd"]


async def test_run_task_forwards_extra_args():
    """Extra args (e.g. --global) are forwarded between the exe and task name."""
    _register_project("default", exe=None, extra_args=["--global"])
    proc = _make_proc_mock([], [], returncode=0)
    captured_cmd = {}

    async def fake_exec(*cmd, **kwargs):
        captured_cmd["cmd"] = cmd
        return proc

    with patch("asyncio.create_subprocess_exec", fake_exec):
        async with Client(mcp) as client:
            await client.call_tool("run_task", {"task_name": "hello"})

    cmd = captured_cmd["cmd"]
    assert "--global" in cmd
    # --global must appear before the task name
    assert cmd.index("--global") < cmd.index("hello")


# ---------------------------------------------------------------------------
# args_schema in task metadata
# ---------------------------------------------------------------------------


async def test_list_tasks_args_schema_is_list():
    """Every task returned by list_tasks must include a valid args_schema list."""
    fake_tasks = [
        {
            "name": "install",
            "aliases": ["install"],
            "short_help": "Install.",
            "help": "Install.",
            "usage": "usage: qk install [-h] [--editable]",
            "location": "_qk/__init__.py:1",
            "args_schema": [
                {
                    "flags": ["--editable", "-e"],
                    "dest": "editable",
                    "type": None,
                    "default": False,
                    "required": False,
                    "choices": None,
                    "help": "Install as editable",
                    "nargs": 0,
                }
            ],
        }
    ]
    _register_project(
        "myproject", exe=Path("/project/.venv/bin/qk"), root=Path("/project")
    )
    with patch(
        "asyncio.create_subprocess_exec",
        AsyncMock(return_value=_fake_list_proc(fake_tasks)),
    ):
        async with Client(mcp) as client:
            result = await client.call_tool("list_tasks", {})
    for entry in result.data:
        for task in entry["tasks"]:
            schema = task.get("args_schema")
            assert isinstance(schema, list), f"{task['name']} missing args_schema list"
            for arg in schema:
                assert "flags" in arg
                assert "dest" in arg
                assert "required" in arg


# ---------------------------------------------------------------------------
# main() — project discovery
# ---------------------------------------------------------------------------


def test_main_project_discovers_exe_from_path(tmp_path):
    """--project discovers the local exe starting from the module's parent dir.

    This covers the case where the MCP host starts the process with CWD set
    to an unrelated directory (e.g. the user's home folder) while the project
    lives elsewhere.
    """
    # Build a fake project tree: tmp_path/myproject/_qk/.venv/bin/qk
    project_dir = tmp_path / "myproject"
    qk_dir = project_dir / "_qk"
    fake_venv = qk_dir / ".venv" / "bin"
    fake_venv.mkdir(parents=True)
    fake_exe = fake_venv / "qk"
    fake_exe.touch(mode=0o755)
    # Write a minimal pyvenv.cfg so _resolve_uv_venv recognises it as a uv venv
    (qk_dir / ".venv" / "pyvenv.cfg").write_text("home = /usr/bin\nuv = true\n")

    with patch("sys.argv", ["qk-mcp", "--project", f"myproject:{qk_dir}"]):
        with patch("quickie.mcp.mcp") as mock_mcp:
            mock_mcp.run = MagicMock()
            main()

    assert "myproject" in _projects
    assert _projects["myproject"].qk_exe == fake_exe


def test_main_project_flag(tmp_path):
    """--project alias:path registers the project under that alias."""
    qk_dir = tmp_path / "_qk"
    qk_dir.mkdir()

    with patch("sys.argv", ["qk-mcp", "--project", f"myapp:{qk_dir}"]):
        with patch("quickie.mcp.mcp") as mock_mcp:
            mock_mcp.run = MagicMock()
            with patch("quickie.mcp.Launcher") as MockLauncher:
                instance = MockLauncher.return_value
                instance.discover_project_root.return_value = tmp_path
                instance.resolve_executable.return_value = None
                main()

    assert "myapp" in _projects
    assert _projects["myapp"].project_root == tmp_path


def test_main_config_toml(tmp_path):
    """--config with a TOML file loads project entries."""
    qk_dir = tmp_path / "_qk"
    qk_dir.mkdir()
    config_file = tmp_path / "projects.toml"
    config_file.write_text(f'[projects]\nmyapp = "{qk_dir}"\n')

    with patch("sys.argv", ["qk-mcp", "--config", str(config_file)]):
        with patch("quickie.mcp.mcp") as mock_mcp:
            mock_mcp.run = MagicMock()
            with patch("quickie.mcp.Launcher") as MockLauncher:
                instance = MockLauncher.return_value
                instance.discover_project_root.return_value = tmp_path
                instance.resolve_executable.return_value = None
                main()

    assert "myapp" in _projects


def test_main_config_json(tmp_path):
    """--config with a JSON file loads project entries."""
    qk_dir = tmp_path / "_qk"
    qk_dir.mkdir()
    config_file = tmp_path / "projects.json"
    config_file.write_text(json.dumps({"projects": {"myapp": str(qk_dir)}}))

    with patch("sys.argv", ["qk-mcp", "--config", str(config_file)]):
        with patch("quickie.mcp.mcp") as mock_mcp:
            mock_mcp.run = MagicMock()
            with patch("quickie.mcp.Launcher") as MockLauncher:
                instance = MockLauncher.return_value
                instance.discover_project_root.return_value = tmp_path
                instance.resolve_executable.return_value = None
                main()

    assert "myapp" in _projects


def test_main_project_flag_overrides_config(tmp_path):
    """--project overrides a same-named entry in --config."""
    qk_a = tmp_path / "a" / "_qk"
    qk_a.mkdir(parents=True)
    qk_b = tmp_path / "b" / "_qk"
    qk_b.mkdir(parents=True)

    config_file = tmp_path / "projects.toml"
    config_file.write_text(f'[projects]\nmyapp = "{qk_a}"\n')

    with patch(
        "sys.argv",
        ["qk-mcp", "--config", str(config_file), "--project", f"myapp:{qk_b}"],
    ):
        with patch("quickie.mcp.mcp") as mock_mcp:
            mock_mcp.run = MagicMock()
            with patch("quickie.mcp.Launcher") as MockLauncher:
                instance = MockLauncher.return_value
                instance.discover_project_root.return_value = tmp_path / "b"
                instance.resolve_executable.return_value = None
                main()

    assert "myapp" in _projects
    # --project wins: discovery was called with the b path
    assert _projects["myapp"].project_root == tmp_path / "b"
