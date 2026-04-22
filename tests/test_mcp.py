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

from quickie.config import app
from quickie.mcp import _subprocess_cfg, main, mcp

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_subprocess_cfg():
    """Reset _subprocess_cfg to defaults before each test."""
    original_exe = _subprocess_cfg.qk_exe
    original_args = _subprocess_cfg.extra_args[:]
    yield
    _subprocess_cfg.qk_exe = original_exe
    _subprocess_cfg.extra_args = original_args


@pytest.fixture(autouse=True)
def load_test_tasks(patch_config):  # patch_config is the autouse fixture in conftest
    """Ensure the test task namespace is loaded for every MCP test."""
    app.load_tasks()


# ---------------------------------------------------------------------------
# list_tasks
# ---------------------------------------------------------------------------


async def test_list_tasks_returns_list():
    async with Client(mcp) as client:
        result = await client.call_tool("list_tasks", {})
    assert isinstance(result.data, list)
    assert len(result.data) > 0


async def test_list_tasks_fields():
    async with Client(mcp) as client:
        result = await client.call_tool("list_tasks", {})
    for entry in result.data:
        assert "name" in entry
        assert "aliases" in entry
        assert "short_help" in entry
        assert "help" in entry
        assert "usage" in entry
        assert "location" in entry


async def test_list_tasks_no_duplicates():
    """Each unique task object must appear exactly once."""
    async with Client(mcp) as client:
        result = await client.call_tool("list_tasks", {})
    names = [t["name"] for t in result.data]
    assert len(names) == len(
        set(names)
    ), "Duplicate task names found in list_tasks output"


async def test_list_tasks_contains_hello():
    async with Client(mcp) as client:
        result = await client.call_tool("list_tasks", {})
    names = [t["name"] for t in result.data]
    assert "hello" in names


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
        }
    ]

    proc = MagicMock()
    proc.returncode = 0
    proc.communicate = AsyncMock(return_value=(json.dumps(fake_tasks).encode(), b""))

    captured_cmd = {}

    async def fake_exec(*cmd, **kwargs):
        captured_cmd["cmd"] = cmd
        return proc

    _subprocess_cfg.qk_exe = Path("/project/.venv/bin/qk")
    with patch("asyncio.create_subprocess_exec", fake_exec):
        async with Client(mcp) as client:
            result = await client.call_tool("list_tasks", {})

    assert "--list-json" in captured_cmd["cmd"]
    assert captured_cmd["cmd"][0] == "/project/.venv/bin/qk"
    assert result.data == fake_tasks


async def test_list_tasks_local_exe_error_raises():
    """A non-zero exit from the local exe raises a ToolError."""
    proc = MagicMock()
    proc.returncode = 1
    proc.communicate = AsyncMock(return_value=(b"", b"import error"))

    _subprocess_cfg.qk_exe = Path("/project/.venv/bin/qk")
    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        async with Client(mcp) as client:
            with pytest.raises(Exception):
                await client.call_tool("list_tasks", {})


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
    proc = _make_proc_mock([b"Hello world!\n"], [], returncode=0)
    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        async with Client(mcp) as client:
            result = await client.call_tool("run_task", {"task_name": "hello"})
    assert result.data["exit_code"] == 0
    assert "Hello world!" in result.data["stdout"]


async def test_run_task_with_args():
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
    proc = _make_proc_mock([], [b"error msg\n"], returncode=1)
    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        async with Client(mcp) as client:
            result = await client.call_tool("run_task", {"task_name": "hello"})
    assert result.data["exit_code"] == 1
    assert "error msg" in result.data["stderr"]


async def test_run_task_launcher_env():
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


async def test_run_task_unknown_task():
    async with Client(mcp) as client:
        with pytest.raises(Exception, match="Task not found"):
            await client.call_tool("run_task", {"task_name": "__no_such_task__"})


async def test_run_task_timeout():
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


# ---------------------------------------------------------------------------
# run_task — subprocess exe resolution
# ---------------------------------------------------------------------------


async def test_run_task_uses_local_qk_exe_when_set():
    """When a project-local qk exe is configured it should head the command."""
    proc = _make_proc_mock([], [], returncode=0)
    captured_cmd = {}

    async def fake_exec(*cmd, **kwargs):
        captured_cmd["cmd"] = cmd
        return proc

    _subprocess_cfg.qk_exe = Path("/project/.venv/bin/qk")
    with patch("asyncio.create_subprocess_exec", fake_exec):
        async with Client(mcp) as client:
            await client.call_tool("run_task", {"task_name": "hello"})

    assert captured_cmd["cmd"][0] == "/project/.venv/bin/qk"
    assert "hello" in captured_cmd["cmd"]


async def test_run_task_falls_back_to_sys_executable_when_no_local_exe():
    """When no local exe is resolved, sys.executable -m quickie is used."""
    proc = _make_proc_mock([], [], returncode=0)
    captured_cmd = {}

    async def fake_exec(*cmd, **kwargs):
        captured_cmd["cmd"] = cmd
        return proc

    _subprocess_cfg.qk_exe = None
    _subprocess_cfg.extra_args = []
    with patch("asyncio.create_subprocess_exec", fake_exec):
        async with Client(mcp) as client:
            await client.call_tool("run_task", {"task_name": "hello"})

    assert captured_cmd["cmd"][0] == sys.executable
    assert "-m" in captured_cmd["cmd"]
    assert "quickie" in captured_cmd["cmd"]


async def test_run_task_forwards_extra_args():
    """Extra args (e.g. --global) are forwarded between the exe and task name."""
    proc = _make_proc_mock([], [], returncode=0)
    captured_cmd = {}

    async def fake_exec(*cmd, **kwargs):
        captured_cmd["cmd"] = cmd
        return proc

    _subprocess_cfg.qk_exe = None
    _subprocess_cfg.extra_args = ["--global"]
    with patch("asyncio.create_subprocess_exec", fake_exec):
        async with Client(mcp) as client:
            await client.call_tool("run_task", {"task_name": "hello"})

    cmd = captured_cmd["cmd"]
    assert "--global" in cmd
    # --global must appear before the task name
    assert cmd.index("--global") < cmd.index("hello")


# ---------------------------------------------------------------------------
# main() — project discovery
# ---------------------------------------------------------------------------


def test_main_discovers_from_module_path_not_cwd(tmp_path):
    """When --module is given, discovery starts from the module's parent dir.

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

    # Patch argv so MCPArgumentParser picks up --module pointing at qk_dir
    with patch("sys.argv", ["qk-mcp", "--module", str(qk_dir)]):
        with patch("quickie.mcp.mcp") as mock_mcp:
            mock_mcp.run = MagicMock()
            main()

    assert _subprocess_cfg.qk_exe == fake_exe
