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


class TestLauncherCache:
    """Tests for project root discovery cache."""

    def setup_method(self):
        """Clear cache before each test."""
        Launcher._invalidate_cache()

    def test_cache_hit_skips_walk(self, tmp_path):
        """Test that a cached result skips the directory walk."""
        qk_dir = tmp_path / "_qk"
        qk_dir.mkdir()
        (qk_dir / "__init__.py").touch()

        launcher = Launcher()
        result1 = launcher.discover_project_root(start_path=tmp_path)
        assert result1 == tmp_path

        # Second call should hit cache and not call _walk_for_project_root
        with patch.object(Launcher, "_walk_for_project_root") as mock_walk:
            result2 = launcher.discover_project_root(start_path=tmp_path)
            assert result2 == tmp_path
            mock_walk.assert_not_called()

    def test_cache_hit_for_not_found_skips_walk(self, tmp_path):
        """Test that a cached not-found result skips the walk and still returns None."""
        launcher = Launcher()
        result1 = launcher.discover_project_root(start_path=tmp_path)
        assert result1 is None

        # Second call should hit cache and not call _walk_for_project_root
        with patch.object(Launcher, "_walk_for_project_root") as mock_walk:
            result2 = launcher.discover_project_root(start_path=tmp_path)
            assert result2 is None
            mock_walk.assert_not_called()

    def test_cache_invalidation_on_mtime_change(self, tmp_path):
        """Test that a stale mtime causes the cache to be bypassed."""
        import time

        qk_dir = tmp_path / "_qk"
        qk_dir.mkdir()
        (qk_dir / "__init__.py").touch()

        launcher = Launcher()
        result1 = launcher.discover_project_root(start_path=tmp_path)
        assert result1 == tmp_path

        # Record the cached mtime
        cached_mtime = Launcher._root_cache[tmp_path.resolve()][1]

        # Touch the _qk dir so its mtime advances
        time.sleep(0.01)
        qk_dir.touch()
        current_mtime = qk_dir.stat().st_mtime

        assert current_mtime > cached_mtime, "mtime should have advanced after touch"

        # The cache entry is now stale — _walk_for_project_root must be called
        with patch.object(
            Launcher, "_walk_for_project_root", wraps=Launcher._walk_for_project_root
        ) as mock_walk:
            result2 = launcher.discover_project_root(start_path=tmp_path)
            assert result2 == tmp_path
            mock_walk.assert_called_once()

    def test_cache_invalidation_on_marker_removal(self, tmp_path):
        """Test that removing the marker invalidates the cache."""
        import shutil

        qk_dir = tmp_path / "_qk"
        qk_dir.mkdir()
        (qk_dir / "__init__.py").touch()

        launcher = Launcher()
        result1 = launcher.discover_project_root(start_path=tmp_path)
        assert result1 == tmp_path

        # Remove the marker
        shutil.rmtree(qk_dir)

        # The cached marker no longer exists — cache must be bypassed
        with patch.object(
            Launcher, "_walk_for_project_root", wraps=Launcher._walk_for_project_root
        ) as mock_walk:
            result2 = launcher.discover_project_root(start_path=tmp_path)
            assert result2 is None
            mock_walk.assert_called_once()

    def test_cache_not_found_validated_via_has_qk_marker(self, tmp_path):
        """Test that a cached not-found result checks for new markers."""
        launcher = Launcher()
        result1 = launcher.discover_project_root(start_path=tmp_path)
        assert result1 is None

        # Create a _qk dir after the first call — cache should notice
        qk_dir = tmp_path / "_qk"
        qk_dir.mkdir()
        (qk_dir / "__init__.py").touch()

        # _has_qk_marker will return True, so _walk_for_project_root is called
        with patch.object(
            Launcher, "_walk_for_project_root", wraps=Launcher._walk_for_project_root
        ) as mock_walk:
            result2 = launcher.discover_project_root(start_path=tmp_path)
            assert result2 == tmp_path
            mock_walk.assert_called_once()

    def test_invalidate_cache_clears_all(self, tmp_path):
        """Test that _invalidate_cache clears the entire cache."""
        qk_dir = tmp_path / "_qk"
        qk_dir.mkdir()
        (qk_dir / "__init__.py").touch()

        launcher = Launcher()
        launcher.discover_project_root(start_path=tmp_path)
        assert tmp_path.resolve() in Launcher._root_cache

        Launcher._invalidate_cache()
        assert len(Launcher._root_cache) == 0

    def test_walk_for_project_root_oserror_on_stat(self, tmp_path):
        """Test OSError handling in _walk_for_project_root."""
        qk_dir = tmp_path / "_qk"
        qk_dir.mkdir()
        (qk_dir / "__init__.py").touch()

        with patch.object(Path, "stat", side_effect=OSError("Permission denied")):
            result, mtime = Launcher._walk_for_project_root(tmp_path)
            # Should still find the directory, just with mtime=0.0
            assert result == tmp_path
            assert mtime == 0.0

    def test_walk_for_project_root_reaches_root(self, tmp_path, monkeypatch):
        """Test that walk stops at filesystem root."""
        # Start from a path that has no _qk anywhere
        monkeypatch.chdir(tmp_path)
        result, mtime = Launcher._walk_for_project_root(tmp_path)
        # Should return None when reaching root without finding _qk
        assert result is None
        assert mtime == 0.0

    def test_has_qk_marker_with_directory(self, tmp_path):
        """Test _has_qk_marker with _qk directory."""
        qk_dir = tmp_path / "_qk"
        qk_dir.mkdir()
        assert Launcher._has_qk_marker(tmp_path) is True

    def test_has_qk_marker_with_file(self, tmp_path):
        """Test _has_qk_marker with _qk.py file."""
        qk_file = tmp_path / "_qk.py"
        qk_file.touch()
        assert Launcher._has_qk_marker(tmp_path) is True

    def test_has_qk_marker_returns_false(self, tmp_path):
        """Test _has_qk_marker returns False when no marker exists."""
        assert Launcher._has_qk_marker(tmp_path) is False

    def test_cache_with_qk_py_file(self, tmp_path):
        """Test caching works with _qk.py file marker."""
        qk_file = tmp_path / "_qk.py"
        qk_file.touch()

        launcher = Launcher()
        result1 = launcher.discover_project_root(start_path=tmp_path)
        assert result1 == tmp_path

        # Second call should hit cache
        with patch.object(Launcher, "_walk_for_project_root") as mock_walk:
            result2 = launcher.discover_project_root(start_path=tmp_path)
            assert result2 == tmp_path
            mock_walk.assert_not_called()
