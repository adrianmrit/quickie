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
import os
import sys

from fastmcp import FastMCP, Context
from fastmcp.dependencies import CurrentContext
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from quickie._argparser import MCPArgumentParser
from quickie.config import app

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
def list_tasks() -> list[dict]:
    """Return metadata for every non-private task registered in this project."""
    cwd = os.getcwd()

    # De-duplicate: multiple names may point to the same task object.
    seen: dict[int, dict] = {}
    for invocation_name, task in app.tasks.items():
        task_id = id(task)
        if task_id not in seen:
            seen[task_id] = {
                "name": task.name,
                "aliases": [],
                "short_help": task.get_short_help(),
                "help": task.get_help(),
                "usage": task.parser.format_usage().strip(),
                "location": task._get_relative_file_location(cwd),
            }
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
    if task_name not in app.tasks:
        raise ToolError(
            f"Task not found: '{task_name}'. Call list_tasks to see available tasks."
        )

    await ctx.info(
        f"Running task '{task_name}'" + (f" with args {args}" if args else "")
    )

    stdin_pipe = (
        asyncio.subprocess.PIPE if stdin is not None else asyncio.subprocess.DEVNULL
    )

    # Build command: only include the `--` separator when extra args are given.
    cmd = [sys.executable, "-m", "quickie", task_name]
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

    app.load_tasks()
    mcp.run()  # stdio transport by default


if __name__ == "__main__":
    main()
