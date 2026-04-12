"""Integration tests for launcher project discovery and delegation."""

import platform
from pathlib import Path
from unittest.mock import patch

import pytest

from quickie._launcher import (
    Launcher,
    ProjectNotFoundError,
    ExecutableNotFoundError,
)

# Exit code constants
LAUNCHER_ERROR_CODE = 2


class TestLauncherProjectDiscovery:
    """Tests for project discovery functionality."""

    def test_discover_qk_directory(self, tmp_path, monkeypatch):
        """Test discovery of _qk directory."""
        # Create project structure
        qk_dir = tmp_path / "_qk"
        qk_dir.mkdir()
        (qk_dir / "__init__.py").touch()

        # Change to project directory
        monkeypatch.chdir(tmp_path)

        launcher = Launcher()
        result = launcher.discover_project_root()

        assert result == tmp_path
        assert launcher.project_root == tmp_path

    def test_discover_qk_file(self, tmp_path, monkeypatch):
        """Test discovery of _qk.py file."""
        qk_file = tmp_path / "_qk.py"
        qk_file.touch()

        monkeypatch.chdir(tmp_path)

        launcher = Launcher()
        result = launcher.discover_project_root()

        assert result == tmp_path

    def test_discover_traverses_parent_dirs(self, tmp_path, monkeypatch):
        """Test that discovery traverses parent directories."""
        # Create nested structure:
        # tmp_path/
        #   _qk/
        #   subdir/
        #     subsubdir/
        qk_dir = tmp_path / "_qk"
        qk_dir.mkdir()
        (qk_dir / "__init__.py").touch()

        subdir = tmp_path / "subdir" / "subsubdir"
        subdir.mkdir(parents=True)

        # Change to nested subdirectory
        monkeypatch.chdir(subdir)

        launcher = Launcher()
        result = launcher.discover_project_root()

        assert result == tmp_path

    def test_discover_returns_none_when_not_found(self, tmp_path, monkeypatch):
        """Test that discovery returns None when no project found."""
        monkeypatch.chdir(tmp_path)

        launcher = Launcher()
        result = launcher.discover_project_root()

        assert result is None
        assert launcher.project_root is None

    def test_discover_with_explicit_start_path(self, tmp_path):
        """Test project discovery with explicit start path."""
        # Create project structure
        project = tmp_path / "my_project"
        project.mkdir()
        qk_dir = project / "_qk"
        qk_dir.mkdir()
        (qk_dir / "__init__.py").touch()

        launcher = Launcher()
        result = launcher.discover_project_root(start_path=project / "src")

        assert result == project


class TestLauncherExecutableResolution:
    """Tests for executable resolution functionality."""

    def test_resolve_generic_venv_unix(self, tmp_path):
        """Test resolution of qk executable in generic .venv on Unix."""
        if platform.system() == "Windows":
            pytest.skip("Unix-specific test")

        # Create venv structure
        project = tmp_path / "project"
        project.mkdir()
        venv = project / ".venv"
        bin_dir = venv / "bin"
        bin_dir.mkdir(parents=True)
        qk_exe = bin_dir / "qk"
        qk_exe.touch()

        launcher = Launcher()
        launcher.project_root = project
        result = launcher.resolve_executable(project)

        assert result == qk_exe

    def test_resolve_generic_venv_windows(self, tmp_path):
        """Test resolution of qk executable in generic .venv on Windows."""
        if platform.system() != "Windows":
            pytest.skip("Windows-specific test")

        # Create venv structure
        project = tmp_path / "project"
        project.mkdir()
        venv = project / ".venv"
        scripts_dir = venv / "Scripts"
        scripts_dir.mkdir(parents=True)
        qk_exe = scripts_dir / "qk.exe"
        qk_exe.touch()

        launcher = Launcher()
        launcher.project_root = project
        result = launcher.resolve_executable(project)

        assert result == qk_exe

    def test_resolve_from_env_variable(self, tmp_path, monkeypatch):
        """Test resolution from QK_EXECUTABLE environment variable."""
        project = tmp_path / "project"
        project.mkdir()

        # Set environment variable pointing to custom location
        custom_qk = tmp_path / "custom_qk"
        custom_qk.touch()
        monkeypatch.setenv("QK_EXECUTABLE", str(custom_qk))

        launcher = Launcher()
        launcher.project_root = project
        result = launcher.resolve_executable(project)

        assert result == custom_qk

    def test_resolve_returns_none_when_not_found(self, tmp_path):
        """Test that resolution returns None when executable not found."""
        project = tmp_path / "project"
        project.mkdir()

        launcher = Launcher()
        launcher.project_root = project
        result = launcher.resolve_executable(project)

        assert result is None

    def test_resolve_prefers_venv_over_env_var(self, tmp_path, monkeypatch):
        """Test that existing venv is preferred over env variable."""
        if platform.system() == "Windows":
            pytest.skip("Unix-specific test")

        project = tmp_path / "project"
        project.mkdir()

        # Create venv
        venv = project / ".venv"
        bin_dir = venv / "bin"
        bin_dir.mkdir(parents=True)
        qk_exe = bin_dir / "qk"
        qk_exe.touch()

        # Also set environment variable
        env_var_qk = tmp_path / "env_qk"
        env_var_qk.touch()
        monkeypatch.setenv("QK_EXECUTABLE", str(env_var_qk))

        launcher = Launcher()
        launcher.project_root = project
        result = launcher.resolve_executable(project)

        # Should prefer venv over env variable
        assert result == qk_exe


class TestLauncherRecursionGuard:
    """Tests for recursion guard functionality."""

    def test_recursion_guard_not_set_initially(self, monkeypatch):
        """Test that recursion guard is not set initially."""
        monkeypatch.delenv("QK_LAUNCHER_RUNNING", raising=False)
        launcher = Launcher()
        assert not launcher.is_in_recursion()

    def test_set_recursion_guard(self):
        """Test setting the recursion guard."""
        launcher = Launcher()
        launcher.set_recursion_guard()
        assert launcher.is_in_recursion()

    def test_recursion_guard_env_var(self, monkeypatch):
        """Test that recursion guard uses environment variable."""
        monkeypatch.setenv("QK_LAUNCHER_RUNNING", "true")

        launcher = Launcher()
        assert launcher.is_in_recursion()

    def test_recursion_guard_false_when_env_not_set(self, monkeypatch):
        """Test recursion guard is false when env var not set."""
        monkeypatch.delenv("QK_LAUNCHER_RUNNING", raising=False)

        launcher = Launcher()
        assert not launcher.is_in_recursion()


class TestLauncherErrorHandling:
    """Tests for launcher error handling."""

    def test_project_not_found_error_message(self, tmp_path):
        """Test ProjectNotFoundError message."""
        cwd = tmp_path / "project"
        cwd.mkdir()

        error = ProjectNotFoundError(cwd)
        assert "No quickie project found" in str(error)
        assert str(cwd) in str(error)
        assert "qk --init" in str(error)
        assert error.exit_code == LAUNCHER_ERROR_CODE

    def test_executable_not_found_error_message(self, tmp_path):
        """Test ExecutableNotFoundError message."""
        project = tmp_path / "project"
        project.mkdir()

        error = ExecutableNotFoundError(project)
        assert "Could not find quickie executable" in str(error)
        assert str(project) in str(error)
        assert error.exit_code == LAUNCHER_ERROR_CODE

    def test_executable_not_found_with_attempted_paths(self, tmp_path):
        """Test ExecutableNotFoundError with attempted paths."""
        project = tmp_path / "project"
        project.mkdir()

        path1 = tmp_path / "path1"
        path2 = tmp_path / "path2"

        error = ExecutableNotFoundError(project, [path1, path2])
        error_str = str(error)
        assert str(path1) in error_str
        assert str(path2) in error_str


class TestLauncherIntegration:
    """Integration tests for launcher flow."""

    def test_launch_succeeds_with_project_found(self, tmp_path, monkeypatch):
        """Test that launch can discover project."""
        # Create project with _qk directory
        qk_dir = tmp_path / "_qk"
        qk_dir.mkdir()
        (qk_dir / "__init__.py").touch()

        monkeypatch.chdir(tmp_path)

        launcher = Launcher()
        # We don't actually delegate, just test discovery
        project = launcher.discover_project_root()
        assert project == tmp_path

        # Now test resolve doesn't raise
        # (won't find executable, but that's ok for this test)
        try:
            launcher.resolve_executable(project)
        except ExecutableNotFoundError:
            # Expected when no venv
            pass

    def test_launch_raises_when_project_not_found(self, tmp_path, monkeypatch):
        """Test that launch raises when no project found."""
        monkeypatch.chdir(tmp_path)

        launcher = Launcher()
        with pytest.raises(ProjectNotFoundError):
            launcher.launch([])

    def test_launch_falls_back_to_current_binary_when_no_executable(
        self, tmp_path, monkeypatch
    ):
        """Test that launch falls back to current binary when no local executable found."""
        # Create project but no venv
        qk_dir = tmp_path / "_qk"
        qk_dir.mkdir()
        (qk_dir / "__init__.py").touch()

        monkeypatch.chdir(tmp_path)

        launcher = Launcher()
        with patch.object(launcher, "delegate", return_value=0) as mock_delegate:
            result = launcher.launch([])
            assert result == 0
            mock_delegate.assert_called_once()
            # Falls back to the currently-running binary
            called_exe = mock_delegate.call_args[0][0]
            assert isinstance(called_exe, Path)
