"""Launcher module for smart qk project detection and delegation."""

import os
import platform
import subprocess
import sys
from pathlib import Path

from quickie import app
from quickie.errors import QuickieError


class ProjectNotFoundError(QuickieError):
    """Raised when no project with pinned quickie is found."""

    def __init__(self, cwd: Path, attempted_paths: list[Path] | None = None):
        """Initialize the error.

        :param cwd: The current working directory.
        :param attempted_paths: Paths that were checked.
        """
        self.cwd = cwd
        self.attempted_paths = attempted_paths or []
        paths_str = (
            "\n  ".join(str(p) for p in self.attempted_paths)
            if self.attempted_paths
            else "  (none checked)"
        )
        message = (
            f"No quickie project found in {cwd} or parent directories.\n\n"
            f"Attempted paths:\n  {paths_str}\n\n"
            f"To initialize a quickie project, run:\n"
            f"  qk --init"
        )
        super().__init__(message, exit_code=2)


class ExecutableNotFoundError(QuickieError):
    """Raised when no qk executable can be resolved from project environment."""

    def __init__(self, project_root: Path, attempted_paths: list[Path] | None = None):
        """Initialize the error.

        :param project_root: The project root where _qk was found.
        :param attempted_paths: Paths where executable was searched.
        """
        self.project_root = project_root
        self.attempted_paths = attempted_paths or []
        paths_str = (
            "\n  ".join(str(p) for p in self.attempted_paths)
            if self.attempted_paths
            else "  (none)"
        )
        message = (
            "Could not find quickie executable in "
            f"project environment at {project_root}.\n\n"
            f"Searched locations:\n  {paths_str}\n\n"
            f"Make sure your virtual environment is initialized:\n"
            f"  cd {project_root}\n"
            f"  python -m venv .venv\n"
            f"  .venv/bin/pip install -e .\n"
            f"\n"
            f"Or with uv:\n"
            f"  uv venv\n"
            f"  uv pip install -e ."
        )
        super().__init__(message, exit_code=2)


class Launcher:
    """Smart launcher for discovering project and delegating."""

    # Environment variable guard to prevent infinite recursion
    _RECURSION_GUARD_ENV = "QK_LAUNCHER_RUNNING"

    def __init__(self):
        """Initialize the launcher."""
        self.project_root: Path | None = None
        self.executable_path: Path | None = None

    def is_in_recursion(self) -> bool:
        """Check if we're already in a delegated execution."""
        return os.environ.get(self._RECURSION_GUARD_ENV) == "true"

    def set_recursion_guard(self):
        """Set the recursion guard to prevent re-entry."""
        os.environ[self._RECURSION_GUARD_ENV] = "true"

    def discover_project_root(self, start_path: Path | None = None) -> Path | None:
        """Discover project root by searching for _qk directory or file.

        :param start_path: Path to start search from. Defaults to current directory.
        :return: Path to project root, or None if not found.
        """
        if start_path is None:
            start_path = Path.cwd()

        current = start_path
        attempted = []

        while True:
            qk_dir = current / "_qk"
            attempted.append(qk_dir)
            if qk_dir.is_dir():
                self.project_root = current
                app.logger.debug(f"Found project root at {current}")
                return current

            qk_file = current / "_qk.py"
            attempted.append(qk_file)
            if qk_file.is_file():
                self.project_root = current
                app.logger.debug(f"Found project root at {current}")
                return current

            if current == current.parent:
                app.logger.debug(f"No project found. Attempted: {attempted}")
                self.project_root = None
                return None

            current = current.parent

    def resolve_executable(self, project_root: Path) -> Path | None:
        """Resolve qk executable from project environment.

        Checks in order (prefers _qk-level venvs):
        1. All venv types in _qk
        2. All venv types at project root
        3. QK_EXECUTABLE environment variable

        :param project_root: The project root directory.
        :return: Path to qk executable, or None if not resolved.
        """
        qk_path = project_root / "_qk"

        if qk_path.exists():
            qk_exe = self._find_qk_executable_in_path(qk_path)
            if qk_exe:
                self.executable_path = qk_exe
                app.logger.debug(f"Found qk executable at {qk_exe}")
                return qk_exe

        qk_exe = self._find_qk_executable_in_path(project_root)
        if qk_exe:
            self.executable_path = qk_exe
            app.logger.debug(f"Found qk executable at {qk_exe}")
            return qk_exe

        env_override = os.environ.get("QK_EXECUTABLE")
        if env_override and Path(env_override).exists():
            self.executable_path = Path(env_override)
            app.logger.debug("Using qk executable from QK_EXECUTABLE")
            return Path(env_override)

        app.logger.debug("Could not resolve qk executable")
        self.executable_path = None
        return None

    def _find_qk_executable_in_path(self, base_path: Path) -> Path | None:
        """Search for qk executable in uv or generic venvs.

        Checks (in order): uv-managed, .venv, venv folders.

        :param base_path: Directory to search for venvs.
        :return: Path to qk executable, or None if not found.
        """
        uv_venv = self._resolve_uv_venv(base_path)
        if uv_venv:
            qk_exe = self._get_executable_path(uv_venv)
            if qk_exe.exists():
                return qk_exe
        for venv_name in [".venv", "venv"]:
            venv_path = base_path / venv_name
            if venv_path.exists():
                qk_exe = self._get_executable_path(venv_path)
                if qk_exe.exists():
                    return qk_exe
        return None

    def _resolve_uv_venv(self, project_root: Path) -> Path | None:
        """Try to detect uv-managed virtual environment.

        :param project_root: The project root directory.
        :return: Path to virtual environment, or None if not found/detected.
        """
        venv_path = project_root / ".venv"
        pyvenv_cfg = venv_path / "pyvenv.cfg"

        if pyvenv_cfg.exists():
            try:
                with open(pyvenv_cfg) as f:
                    if "uv" in f.read().lower():
                        return venv_path
            except OSError:
                pass

        return None

    def _get_executable_path(self, venv_root: Path) -> Path:
        """Get the path to qk executable in a virtual environment.

        :param venv_root: Root of the virtual environment.
        :return: Path to qk executable (may not exist yet).
        """
        if platform.system() == "Windows":
            return venv_root / "Scripts" / "qk.exe"
        return venv_root / "bin" / "qk"

    def delegate(self, executable: Path, argv: list[str]) -> int:
        """Delegate execution to resolved quickie executable.

        :param executable: Path to the qk executable.
        :param argv: Arguments to pass to the executable.
        :return: Exit code from delegated process.
        """
        if not executable.exists():
            raise ExecutableNotFoundError(self.project_root or Path.cwd(), [executable])

        try:
            self.set_recursion_guard()
            if platform.system() == "Windows":
                result = subprocess.run(
                    [str(executable)] + argv,
                    env=os.environ.copy(),
                    check=False,
                )
                return result.returncode
            else:
                # os.execv replaces the current process, preserving signal handling
                os.execv(str(executable), [str(executable)] + argv)
        except OSError as e:
            raise ExecutableNotFoundError(
                self.project_root or Path.cwd(),
                [executable],
            ) from e

    def launch(self, argv: list[str]) -> int:
        """Discover project and delegate if found.

        :param argv: Command-line arguments.
        :return: Exit code from delegated process, or raises error if not delegated.
        """
        project_root = self.discover_project_root()
        if project_root is None:
            raise ProjectNotFoundError(Path.cwd())

        executable = self.resolve_executable(project_root)
        if executable is None:
            # No project-local venv found; fall back to the currently-running
            # qk binary so pipx/global installs work without a local venv.
            executable = Path(sys.argv[0]).resolve()
            app.logger.debug(f"No local executable found; falling back to {executable}")

        return self.delegate(executable, argv)
