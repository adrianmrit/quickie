"""MCP stdio server exposing quickie tasks via FastMCP.

Start with:
    qk-mcp

Then connect any MCP-compatible client (Claude Desktop, Copilot, etc.) via
stdio transport.  The server exposes two tools:

- ``list_tasks``  – discover all available tasks and their arguments.
- ``run_task``    – execute a task by name, streaming output to the client in
                    real time and returning the final captured result.

Projects are registered at server startup via ``--project`` or ``--config``.
A single server can expose tasks from multiple projects simultaneously.
"""

import asyncio
import dataclasses
import json
import os
import sys
import tomllib
from pathlib import Path

from fastmcp import FastMCP, Context
from fastmcp.dependencies import CurrentContext
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from quickie._argparser import MCPArgumentParser
from quickie._launcher import Launcher
from quickie.config import app


# ---------------------------------------------------------------------------
# Project registry (populated once in main(), then read-only)
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class _Project:
    """A resolved project entry registered at server startup."""

    name: str
    extra_args: list[str]
    project_root: Path | None
    qk_exe: Path | None


# alias → _Project; populated in main(), read-only after that.
_projects: dict[str, _Project] = {}


def _lookup_project(project: str | None) -> _Project:
    """Return the ``_Project`` for *project*, or the sole project when *project* is ``None``.

    :param project: Project alias or path prefix.  ``None`` succeeds only when
        exactly one project is registered; otherwise raises :class:`ToolError`.
    :raises ToolError: When *project* does not match any registered project, or
        when *project* is ``None`` and multiple (or zero) projects are registered.
    """
    if project is None:
        if len(_projects) == 1:
            return next(iter(_projects.values()))
        if not _projects:
            raise ToolError(
                "No projects are configured. "
                "Start qk-mcp with --project or --config."
            )
        names = ", ".join(f"'{n}'" for n in _projects)
        raise ToolError(
            "Multiple projects are configured; pass 'project' to select one. "
            f"Available: {names}"
        )

    # 1. Exact alias match.
    if project in _projects:
        return _projects[project]

    # 2. Path-based match: project resolves to the project root or a path under it.
    resolved = Path(project).resolve()
    for proj in _projects.values():
        if proj.project_root is not None:
            try:
                resolved.relative_to(proj.project_root)
                return proj
            except ValueError:
                pass

    names = ", ".join(f"'{n}'" for n in _projects)
    raise ToolError(f"No project found matching '{project}'. " f"Available: {names}")


# ---------------------------------------------------------------------------
# Config file loading
# ---------------------------------------------------------------------------


def _load_config(path: str) -> dict:
    """Load a TOML (``.toml``) or JSON (``.json``) config file.

    :param path: Path to the file.  Extension determines format.
    :returns: Parsed config as a plain :class:`dict`.
    """
    p = Path(path)
    if p.suffix.lower() == ".json":
        return json.loads(p.read_text(encoding="utf-8"))
    with open(p, "rb") as f:
        return tomllib.load(f)


# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------


async def _fetch_tasks(project: _Project) -> list[dict]:
    """Spawn a subprocess to list tasks for *project* and return the parsed list."""
    if project.qk_exe is not None:
        cmd_prefix = [str(project.qk_exe)]
        cwd_for_proc = None
    else:
        cmd_prefix = [sys.executable, "-m", "quickie"]
        cwd_for_proc = str(project.project_root) if project.project_root else None

    proc = await asyncio.create_subprocess_exec(
        *cmd_prefix,
        *project.extra_args,
        "-qqqqqqqqqqq",  # quiet mode: suppress all output except the JSON result
        "--list-json",
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd_for_proc,
        env={**os.environ, "QK_LAUNCHER_RUNNING": "true"},
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise ToolError(
            f"Failed to list tasks for project '{project.name}' "
            f"(exit {proc.returncode}):\n" + stderr.decode(errors="replace")
        )
    return json.loads(stdout.decode())


mcp = FastMCP(
    "quickie",
    instructions=(
        "Exposes quickie project tasks defined in _qk/. "
        "Always call list_tasks first to discover available tasks and their "
        "required arguments, then use run_task to execute them. "
        "Pass 'project' to target a specific project when the server manages "
        "multiple projects."
    ),
)


# ---------------------------------------------------------------------------
# list_tasks
# ---------------------------------------------------------------------------


@mcp.tool(
    description=(
        "List all available (non-private) quickie tasks. "
        "Returns one entry per project, each containing the project alias, "
        "absolute project root, and a list of task metadata dicts "
        "(name, aliases, usage, help, argument schema, source location). "
        "Omit 'module' to list all registered projects at once, or pass a "
        "project alias (or path) to list tasks for that project only."
    ),
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def list_tasks(project: str | None = None) -> list[dict]:
    """Return task metadata grouped by project.

    Each entry in the returned list has the keys:
    - ``project``: the project alias.
    - ``project_root``: absolute path of the project, or ``None``.
    - ``tasks``: list of task metadata dicts.

    :param project: Optional project alias or path.  When supplied, only that
        project's tasks are returned.  When omitted, all registered projects
        are listed.
    """
    if project is not None:
        targets = [_lookup_project(project)]
    else:
        if not _projects:
            raise ToolError(
                "No projects are configured. "
                "Start qk-mcp with --project or --config."
            )
        targets = _projects.values()

    results = []
    for proj in targets:
        tasks = await _fetch_tasks(proj)
        results.append(
            {
                "project": proj.name,
                "project_root": (str(proj.project_root) if proj.project_root else None),
                "tasks": tasks,
            }
        )
    return results


# ---------------------------------------------------------------------------
# run_task
# ---------------------------------------------------------------------------


@mcp.tool(
    description=(
        "Execute a quickie task by name. "
        "Streams stdout to the client as info messages and stderr as warnings "
        "in real time. Returns the captured output and exit code when done. "
        "Supply stdin for tasks that require interactive input (e.g. confirmations). "
        "Raises an error if the task is not found or if the timeout is exceeded. "
        "When multiple projects are registered, pass 'module' (alias or path) to "
        "select the target project; omit it only when a single project is configured."
    ),
)
async def run_task(
    task_name: str,
    args: list[str] | None = None,
    stdin: str | None = None,
    timeout: float = 60.0,
    project: str | None = None,
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
    :param project: Optional project alias or path.  Required when multiple
        projects are configured; optional (defaults to the sole project) when
        only one is registered.
    :param ctx: FastMCP context (injected automatically).
    :returns: ``{"exit_code": int, "stdout": str, "stderr": str}``
    """
    args = args or []
    proj = _lookup_project(project)

    await ctx.info(
        f"Running task '{task_name}'" + (f" with args {args}" if args else "")
    )

    stdin_pipe = (
        asyncio.subprocess.PIPE if stdin is not None else asyncio.subprocess.DEVNULL
    )

    # Build command: prefer project-local qk, fall back to sys.executable.
    if proj.qk_exe is not None:
        cmd = [str(proj.qk_exe), *proj.extra_args, task_name]
        cwd_for_proc = None
    else:
        cmd = [sys.executable, "-m", "quickie", *proj.extra_args, task_name]
        cwd_for_proc = str(proj.project_root) if proj.project_root else None
    if args:
        cmd += ["--", *args]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=stdin_pipe,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd_for_proc,
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


def _resolve_project_entry(alias: str, path: str) -> _Project:
    """Resolve a ``(alias, path)`` pair into a :class:`_Project`.

    :param alias: Human-readable project name.
    :param path: Path to the ``_qk`` module/dir.
    """
    launcher = Launcher()
    module_path = Path(path).resolve()
    discovery_start = module_path.parent if module_path.exists() else Path.cwd()
    project_root = launcher.discover_project_root(discovery_start)
    qk_exe = launcher.resolve_executable(project_root) if project_root else None

    app.logger.debug(
        f"Project '{alias}': root={project_root}, "
        + (f"exe={qk_exe}" if qk_exe else "no local exe")
    )
    return _Project(
        name=alias,
        extra_args=["--module", path],
        project_root=project_root,
        qk_exe=qk_exe,
    )


def main() -> None:
    """Entrypoint for the ``qk-mcp`` console script."""
    parser = MCPArgumentParser()
    namespace = parser.parse_args()

    app.set_verbosity(namespace.verbosity)
    if namespace.log_file:
        app.set_log_file(namespace.log_file)

    # Collect (alias, path) pairs from all declaration sources.
    # Later entries win on alias conflict: config < --project.
    raw: dict[str, str] = {}

    # 1. Config file (lowest priority).
    if namespace.config:
        cfg = _load_config(namespace.config)
        for cfg_alias, cfg_path in cfg.get("projects", {}).items():
            raw[cfg_alias] = cfg_path

    # 2. --project alias:path flags (override config on name conflict).
    for spec in namespace.projects or []:
        alias, _, path = spec.partition(":")
        alias = alias.strip()
        path = path.strip()
        if not alias or not path:
            parser.error(f"--project requires 'NAME:PATH' format, got '{spec}'")
        raw[alias] = path

    # 3. CWD-based default when nothing else was specified.
    if not raw:
        launcher = Launcher()
        project_root = launcher.discover_project_root()
        qk_exe = launcher.resolve_executable(project_root) if project_root else None
        alias = project_root.name if project_root else "default"
        _projects[alias] = _Project(
            name=alias,
            extra_args=[],
            project_root=project_root,
            qk_exe=qk_exe,
        )
        app.logger.debug(
            f"CWD project '{alias}': root={project_root}, "
            + (f"exe={qk_exe}" if qk_exe else "no local exe")
        )

    # Resolve all explicitly declared projects.
    for alias, path in raw.items():
        _projects[alias] = _resolve_project_entry(alias, path)

    mcp.run()  # stdio transport by default


if __name__ == "__main__":
    main()
