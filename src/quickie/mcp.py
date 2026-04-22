"""MCP stdio server exposing quickie tasks via FastMCP.

Start with:
    qk-mcp

Then connect any MCP-compatible client (Claude Desktop, Copilot, etc.) via
stdio transport.  The server exposes two tools:

- ``list_tasks``  – discover all available tasks and their arguments.
- ``run_task``    – execute a task by name, streaming output to the client in
                    real time and returning the final captured result.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from fastmcp import FastMCP, Context
from fastmcp.dependencies import CurrentContext
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from quickie._argparser import MCPArgumentParser
from quickie._launcher import Launcher
from quickie.config import app


class _SubprocessConfig:
    """Holds the subprocess command resolved once at server startup.

    Using a mutable object avoids bare ``global`` assignments while still
    letting ``main()`` update state that ``run_task`` reads at call time.
    """

    qk_exe: Path | None = None
    extra_args: list[str] = []


# Singleton resolved in main(); read-only after that.
_subprocess_cfg = _SubprocessConfig()

mcp = FastMCP(
    "quickie",
    instructions=(
        "Exposes quickie project tasks defined in _qk/. "
        "Always call list_tasks first to discover available tasks and their "
        "required arguments, then use run_task to execute them."
    ),
)


# ---------------------------------------------------------------------------
# list_tasks
# ---------------------------------------------------------------------------


@mcp.tool(
    description=(
        "List all available (non-private) quickie tasks for this project. "
        "Returns task names, aliases, usage syntax, help text, and source location."
    ),
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def list_tasks() -> list[dict]:
    """Return metadata for every non-private task registered in this project."""
    cfg = _subprocess_cfg
    if cfg.qk_exe is not None:
        # Delegate to the project-local qk executable so it runs inside the
        # project's own venv (which has all project-specific dependencies).
        proc = await asyncio.create_subprocess_exec(
            str(cfg.qk_exe),
            *cfg.extra_args,
            "-qqqqqqqqqqq",  # quiet mode: suppress all output except the JSON result
            "--list-json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "QK_LAUNCHER_RUNNING": "true"},
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise ToolError(
                f"Failed to list tasks (exit {proc.returncode}):\n"
                + stderr.decode(errors="replace")
            )
        return json.loads(stdout.decode())

    # No project-local exe — enumerate tasks loaded in-process.
    cwd = os.getcwd()

    # De-duplicate: multiple names may point to the same task object.
    seen: dict[int, dict] = {}
    for invocation_name, task in app.tasks.items():
        task_id = id(task)
        if task_id not in seen:
            seen[task_id] = task.to_info_dict(cwd)
        # Collect every invocation name (canonical + aliases) in the aliases list.
        entry = seen[task_id]
        if invocation_name not in entry["aliases"]:
            entry["aliases"].append(invocation_name)

    # Sort by canonical task name for a stable, readable order.
    return sorted(seen.values(), key=lambda t: t["name"])


# ---------------------------------------------------------------------------
# run_task
# ---------------------------------------------------------------------------


@mcp.tool(
    description=(
        "Execute a quickie task by name. "
        "Streams stdout to the client as info messages and stderr as warnings "
        "in real time. Returns the captured output and exit code when done. "
        "Supply stdin for tasks that require interactive input (e.g. confirmations). "
        "Raises an error if the task is not found or if the timeout is exceeded."
    ),
)
async def run_task(
    task_name: str,
    args: list[str] | None = None,
    stdin: str | None = None,
    timeout: float = 60.0,
    ctx: Context = CurrentContext(),
) -> dict:
    """Run a task in an isolated subprocess and stream its output.

    :param task_name: Name (or alias) of the task to run.
    :param args: Command-line arguments to pass to the task.
    :param stdin: Optional string written to the subprocess stdin then closed.
        Use this to supply interactive input (confirmations, menu choices, etc.).
        When omitted the subprocess receives EOF immediately (DEVNULL).
    :param timeout: Maximum wall-clock seconds to wait (default 60). The
        subprocess is killed and a ToolError is raised if exceeded.
    :param ctx: FastMCP context (injected automatically).
    :returns: ``{"exit_code": int, "stdout": str, "stderr": str}``
    """
    args = args or []
    cfg = _subprocess_cfg
    if task_name not in app.tasks:
        # Only reject unknown tasks when we have the in-process registry.
        # When delegating to a project-local exe the subprocess will report
        # the error itself.
        if cfg.qk_exe is None:
            raise ToolError(
                f"Task not found: '{task_name}'."
                " Call list_tasks to see available tasks."
            )

    await ctx.info(
        f"Running task '{task_name}'" + (f" with args {args}" if args else "")
    )

    stdin_pipe = (
        asyncio.subprocess.PIPE if stdin is not None else asyncio.subprocess.DEVNULL
    )

    # Build command using the project-local qk executable when available so
    # that tasks run inside the project's own venv.  Fall back to the
    # currently-running Python only when no local executable was resolved.
    if cfg.qk_exe is not None:
        cmd = [str(cfg.qk_exe), *cfg.extra_args, task_name]
    else:
        cmd = [sys.executable, "-m", "quickie", *cfg.extra_args, task_name]
    if args:
        cmd += ["--", *args]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=stdin_pipe,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, "QK_LAUNCHER_RUNNING": "true"},
    )

    if stdin is not None and proc.stdin is not None:
        proc.stdin.write(stdin.encode())
        await proc.stdin.drain()
        proc.stdin.close()

    stdout_lines: list[str] = []
    stderr_lines: list[str] = []

    async def _drain(stream, lines, log_fn):
        async for raw_line in stream:
            line = raw_line.decode(errors="replace").rstrip("\n")
            lines.append(line)
            await log_fn(line)

    try:
        async with asyncio.timeout(timeout):
            await asyncio.gather(
                _drain(proc.stdout, stdout_lines, ctx.info),
                _drain(proc.stderr, stderr_lines, ctx.warning),
            )
            await proc.wait()
    except TimeoutError:
        proc.kill()
        raise ToolError(
            f"Task '{task_name}' exceeded the {timeout}s timeout and was killed. "
            "You can increase the timeout by passing a larger value to run_task."
        )

    return {
        "exit_code": proc.returncode,
        "stdout": "\n".join(stdout_lines),
        "stderr": "\n".join(stderr_lines),
    }


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    """Entrypoint for the ``qk-mcp`` console script."""
    parser = MCPArgumentParser()
    namespace = parser.parse_args()

    # Apply configuration from parsed arguments
    use_global = namespace.use_global
    if not use_global and namespace.module:
        app.set_project_path(namespace.module)
    app.set_use_global(use_global)
    app.set_verbosity(namespace.verbosity)
    if namespace.log_file:
        app.set_log_file(namespace.log_file)

    # Build the extra flags that must be forwarded to each task subprocess so
    # it uses the same configuration as this server.
    if use_global:
        _subprocess_cfg.extra_args = ["--global"]
    elif namespace.module:
        _subprocess_cfg.extra_args = ["--module", namespace.module]

    # Discover the project-local qk executable so run_task delegates to the
    # correct venv.
    #
    # When --module is given we derive the search root from the module path
    # itself (its parent directory), because the MCP host may start the
    # process with a CWD that is completely unrelated to the project (e.g.
    # the user's home directory).  Resolving the module path against CWD
    # first handles both absolute and relative --module values.
    if not use_global:
        launcher = Launcher()
        if namespace.module:
            module_path = Path(namespace.module).resolve()
            # If --module points to a file/dir, start discovery from its parent;
            # otherwise treat the value as a directory name inside CWD.
            discovery_start = module_path.parent if module_path.exists() else Path.cwd()
        else:
            discovery_start = None  # defaults to CWD inside discover_project_root
        project_root = launcher.discover_project_root(discovery_start)
        if project_root is not None:
            resolved = launcher.resolve_executable(project_root)
            if resolved is not None:
                _subprocess_cfg.qk_exe = resolved
                app.logger.debug(f"qk-mcp will run tasks via {_subprocess_cfg.qk_exe}")
            else:
                app.logger.debug(
                    "No project-local qk executable found; "
                    "falling back to current interpreter."
                )

    # Only load tasks in-process when there is no project-local executable.
    # When a local exe is configured, list_tasks and run_task both delegate to
    # it, so importing the project's modules here (which may require
    # project-specific dependencies) is unnecessary and would fail.
    if _subprocess_cfg.qk_exe is None:
        app.load_tasks()
    mcp.run()  # stdio transport by default


if __name__ == "__main__":
    main()
