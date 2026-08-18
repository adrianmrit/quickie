"""Tests for the file watcher module."""

import time
import threading

from pytest import mark

from quickie._watcher import FileWatcher, _DEFAULT_EXCLUDE
from quickie._argparser import AppArgumentParser


class TestFileWatcherInit:
    """Tests for FileWatcher initialization."""

    def test_default_exclude_patterns(self):
        """Verify default exclude patterns are sensible."""
        assert ".git" in _DEFAULT_EXCLUDE
        assert "__pycache__" in _DEFAULT_EXCLUDE
        assert "*.pyc" in _DEFAULT_EXCLUDE
        assert ".quickie_cache" in _DEFAULT_EXCLUDE
        assert "tmp" in _DEFAULT_EXCLUDE

    def test_custom_exclude(self, tmp_path):
        """Custom exclude patterns override defaults."""
        watcher = FileWatcher(
            watch_paths=["."],
            exclude=["custom_dir"],
            wd=tmp_path,
        )
        assert watcher._exclude == ["custom_dir"]

    def test_default_watch_paths_fallback(self, tmp_path):
        """When no watch paths resolve, fallback to wd."""
        watcher = FileWatcher(
            watch_paths=["nonexistent_dir"],
            wd=tmp_path,
        )
        dirs = watcher._resolve_watch_dirs()
        assert dirs == [tmp_path]

    def test_custom_debounce(self, tmp_path):
        """Custom debounce value is applied to the watcher."""
        watcher = FileWatcher(
            watch_paths=["."],
            wd=tmp_path,
            debounce=1.5,
        )
        assert watcher._debounce == 1.5


class TestFileWatcherExclude:
    """Tests for the exclude filtering."""

    def test_excluded_git(self, tmp_path):
        """Files in .git are excluded."""
        watcher = FileWatcher(
            watch_paths=["."],
            wd=tmp_path,
        )
        assert watcher._is_excluded(str(tmp_path / ".git" / "config"))

    def test_excluded_pycache(self, tmp_path):
        """Files in __pycache__ are excluded."""
        watcher = FileWatcher(
            watch_paths=["."],
            wd=tmp_path,
        )
        assert watcher._is_excluded(str(tmp_path / "__pycache__" / "module.pyc"))

    def test_excluded_pyc_file(self, tmp_path):
        """.pyc files are excluded."""
        watcher = FileWatcher(
            watch_paths=["."],
            wd=tmp_path,
        )
        assert watcher._is_excluded(str(tmp_path / "module.pyc"))

    def test_not_excluded_python_file(self, tmp_path):
        """Regular Python files are not excluded."""
        watcher = FileWatcher(
            watch_paths=["."],
            wd=tmp_path,
        )
        assert not watcher._is_excluded(str(tmp_path / "module.py"))

    def test_custom_exclude_pattern(self, tmp_path):
        """Custom exclude patterns work."""
        watcher = FileWatcher(
            watch_paths=["."],
            exclude=["build"],
            wd=tmp_path,
        )
        assert watcher._is_excluded(str(tmp_path / "build" / "output.js"))
        assert not watcher._is_excluded(str(tmp_path / "src" / "main.py"))


class TestFileWatcherResolve:
    """Tests for watch path resolution."""

    def test_resolve_existing_dir(self, tmp_path):
        """Existing directories are resolved."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        watcher = FileWatcher(
            watch_paths=["src"],
            wd=tmp_path,
        )
        dirs = watcher._resolve_watch_dirs()
        assert src_dir in dirs

    def test_resolve_nonexistent_dir_fallback(self, tmp_path):
        """Non-existent paths fall back to wd."""
        watcher = FileWatcher(
            watch_paths=["nonexistent"],
            wd=tmp_path,
        )
        dirs = watcher._resolve_watch_dirs()
        assert tmp_path in dirs


class TestFileWatcherStartStop:
    """Tests for starting and stopping the watcher."""

    def test_start_stop_cycle(self, tmp_path):
        """Watcher can be started and stopped cleanly."""
        watcher = FileWatcher(
            watch_paths=["."],
            wd=tmp_path,
        )
        watcher.start()
        assert watcher._observer is not None
        assert watcher._observer.is_alive()
        watcher.stop()
        assert watcher._observer is None

    def test_double_start_is_noop(self, tmp_path):
        """Starting twice doesn't create a second observer."""
        watcher = FileWatcher(
            watch_paths=["."],
            wd=tmp_path,
        )
        watcher.start()
        observer1 = watcher._observer
        watcher.start()
        assert watcher._observer is observer1
        watcher.stop()


class TestFileWatcherChanges:
    """Tests for change detection."""

    def test_no_changes_initially(self, tmp_path):
        """No changes detected before any files are modified."""
        watcher = FileWatcher(
            watch_paths=["."],
            wd=tmp_path,
        )
        assert not watcher.has_changes()

    def test_detects_file_modification(self, tmp_path):
        """Modification of a watched file is detected."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("initial")

        watcher = FileWatcher(
            watch_paths=["."],
            wd=tmp_path,
            debounce=0.0,  # No debounce for instant detection in tests
        )
        watcher.start()
        try:
            # Wait for observer to be ready
            time.sleep(0.1)

            # Modify the file
            test_file.write_text("modified")

            # Wait for event to be processed
            time.sleep(0.2)

            assert watcher.has_changes()
        finally:
            watcher.stop()

    def test_detects_new_file(self, tmp_path):
        """Creation of a new file is detected."""
        watcher = FileWatcher(
            watch_paths=["."],
            wd=tmp_path,
            debounce=0.0,
        )
        watcher.start()
        try:
            time.sleep(0.1)

            new_file = tmp_path / "new_file.py"
            new_file.write_text("print('hello')")

            time.sleep(0.2)

            assert watcher.has_changes()
        finally:
            watcher.stop()

    def test_detects_deleted_file(self, tmp_path):
        """Deletion of a file is detected."""
        test_file = tmp_path / "to_delete.txt"
        test_file.write_text("delete me")

        watcher = FileWatcher(
            watch_paths=["."],
            wd=tmp_path,
            debounce=0.0,
        )
        watcher.start()
        try:
            time.sleep(0.1)

            test_file.unlink()

            time.sleep(0.2)

            assert watcher.has_changes()
        finally:
            watcher.stop()

    def test_excluded_files_not_detected(self, tmp_path):
        """Changes to excluded files are not detected."""
        pycache_dir = tmp_path / "__pycache__"
        pycache_dir.mkdir()
        pyc_file = pycache_dir / "module.pyc"
        pyc_file.write_text("cached")

        watcher = FileWatcher(
            watch_paths=["."],
            wd=tmp_path,
            debounce=0.0,
        )
        watcher.start()
        try:
            time.sleep(0.1)

            # Modify the excluded file
            pyc_file.write_text("updated cached")

            time.sleep(0.2)

            # Should NOT detect changes to excluded files
            assert not watcher.has_changes()
        finally:
            watcher.stop()

    def test_reset_clears_state(self, tmp_path):
        """Reset clears the change state."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("initial")

        watcher = FileWatcher(
            watch_paths=["."],
            wd=tmp_path,
            debounce=0.0,
        )
        watcher.start()
        try:
            time.sleep(0.1)

            test_file.write_text("modified")
            time.sleep(0.2)

            assert watcher.has_changes()

            watcher.reset()
            assert not watcher.has_changes()
        finally:
            watcher.stop()

    def test_debounce_cooldown(self, tmp_path):
        """Changes within debounce window are accumulated."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("initial")

        watcher = FileWatcher(
            watch_paths=["."],
            wd=tmp_path,
            debounce=0.5,  # 500ms debounce
        )
        watcher.start()
        try:
            time.sleep(0.1)

            # First modification
            test_file.write_text("modified1")
            time.sleep(0.1)

            # Immediately modify again (within debounce)
            test_file.write_text("modified2")
            time.sleep(0.1)

            # Should NOT report changes yet (within debounce)
            assert not watcher.has_changes()

            # Wait for debounce to expire
            time.sleep(0.5)

            # Now should report changes
            assert watcher.has_changes()
        finally:
            watcher.stop()


class TestFileWatcherThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_modifications(self, tmp_path):
        """Multiple concurrent file modifications are handled safely."""
        # Create some files
        for i in range(5):
            (tmp_path / f"file_{i}.txt").write_text(f"content {i}")

        watcher = FileWatcher(
            watch_paths=["."],
            wd=tmp_path,
            debounce=0.0,
        )
        watcher.start()
        try:
            time.sleep(0.1)

            # Modify files from multiple threads
            def modify_file(idx):
                time.sleep(0.05 * idx)
                (tmp_path / f"file_{idx}.txt").write_text(f"modified {idx}")

            threads = [
                threading.Thread(target=modify_file, args=(i,)) for i in range(5)
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            time.sleep(0.3)

            assert watcher.has_changes()
        finally:
            watcher.stop()


@mark.integration
class TestWatchModeCLI:
    """Integration tests for watch mode CLI arguments."""

    def test_watch_flag_parsed(self):
        """--watch flag is parsed correctly."""
        parser = AppArgumentParser()
        namespace, _ = parser.parse_known_args(["--watch", "my-task"])
        assert namespace.watch is True
        assert namespace.task == "my-task"

    def test_watch_short_flag(self):
        """-w flag is parsed correctly."""
        parser = AppArgumentParser()
        namespace, _ = parser.parse_known_args(["-w", "my-task"])
        assert namespace.watch is True
        assert namespace.task == "my-task"

    def test_watch_paths_parsed(self):
        """--watch-paths is parsed as a list."""
        parser = AppArgumentParser()
        namespace, _ = parser.parse_known_args(
            ["--watch", "--watch-paths", "src/", "--watch-paths", "lib/", "my-task"]
        )
        assert namespace.watch_paths == ["src/", "lib/"]

    def test_watch_exclude_parsed(self):
        """--watch-exclude is parsed as a list."""
        parser = AppArgumentParser()
        namespace, _ = parser.parse_known_args(
            ["--watch", "--watch-exclude", "build/", "my-task"]
        )
        assert namespace.watch_exclude == ["build/"]

    def test_watch_without_task(self):
        """--watch without a task leaves task as None."""
        parser = AppArgumentParser()
        namespace, _ = parser.parse_known_args(["--watch"])
        assert namespace.watch is True
        assert namespace.task is None

    def test_watch_with_task_args(self):
        """--watch with task and task args."""
        parser = AppArgumentParser()
        namespace, _ = parser.parse_known_args(
            ["--watch", "--watch-paths", "src/", "my-task", "--", "extra", "args"]
        )
        assert namespace.watch is True
        assert namespace.task == "my-task"
        assert namespace.args == ["--", "extra", "args"]

    def test_watch_debounce_parsed(self):
        """--watch-debounce is parsed as a float."""
        parser = AppArgumentParser()
        namespace, _ = parser.parse_known_args(
            ["--watch", "--watch-debounce", "1.5", "my-task"]
        )
        assert namespace.watch_debounce == 1.5

    def test_watch_interval_parsed(self):
        """--watch-interval is parsed as a float."""
        parser = AppArgumentParser()
        namespace, _ = parser.parse_known_args(
            ["--watch", "--watch-interval", "0.1", "my-task"]
        )
        assert namespace.watch_interval == 0.1

    def test_watch_defaults_are_none(self):
        """--watch-debounce and --watch-interval default to None."""
        parser = AppArgumentParser()
        namespace, _ = parser.parse_known_args(["--watch", "my-task"])
        assert namespace.watch_debounce is None
        assert namespace.watch_interval is None
