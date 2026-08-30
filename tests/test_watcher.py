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
        assert "**/.git/**" in _DEFAULT_EXCLUDE
        assert "**/__pycache__/**" in _DEFAULT_EXCLUDE
        assert "**/*.pyc" in _DEFAULT_EXCLUDE
        assert "**/.quickie_cache/**" in _DEFAULT_EXCLUDE

    def test_custom_exclude(self, tmp_path):
        """Custom exclude patterns override defaults."""
        watcher = FileWatcher(
            watch_paths=["."],
            ignore_patterns=["custom_dir"],
            wd=tmp_path,
        )
        assert watcher._ignore_patterns == ["custom_dir"]

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
            ignore_paths=[".git"],
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
            ignore_paths=[".git"],
            wd=tmp_path,
        )
        assert watcher._is_ignored(str(tmp_path / ".git" / "config"))

    def test_excluded_pycache(self, tmp_path):
        """Files in __pycache__ are excluded."""
        watcher = FileWatcher(
            watch_paths=["."],
            ignore_paths=["__pycache__"],
            wd=tmp_path,
        )
        assert watcher._is_ignored(str(tmp_path / "__pycache__" / "module.pyc"))

    def test_excluded_pyc_file(self, tmp_path):
        """.pyc files are excluded."""
        watcher = FileWatcher(
            watch_paths=["."],
            ignore_paths=["module.pyc"],
            wd=tmp_path,
        )
        assert watcher._is_ignored(str(tmp_path / "module.pyc"))

    def test_not_excluded_python_file(self, tmp_path):
        """Regular Python files are not excluded."""
        watcher = FileWatcher(
            watch_paths=["."],
            wd=tmp_path,
        )
        assert not watcher._is_ignored(str(tmp_path / "module.py"))

    def test_custom_exclude_pattern(self, tmp_path):
        """Custom exclude patterns work."""
        watcher = FileWatcher(
            watch_paths=["."],
            ignore_paths=["build"],
            wd=tmp_path,
        )
        assert watcher._is_ignored(str(tmp_path / "build" / "output.js"))
        assert not watcher._is_ignored(str(tmp_path / "src" / "main.py"))

    def test_ignored_path_matches_only_below_that_path(self, tmp_path):
        """An ignored directory path excludes its contents."""
        watcher = FileWatcher(
            watch_paths=["."],
            ignore_paths=["tmp"],
            wd=tmp_path,
        )
        assert watcher._is_ignored(str(tmp_path / "tmp" / "out.txt"))
        assert not watcher._is_ignored(str(tmp_path / "src" / "tmp" / "out.txt"))

    def test_ignored_path_does_not_match_ancestor(self, tmp_path):
        """An ignored path does not exclude an ancestor directory."""
        watcher = FileWatcher(
            watch_paths=["."],
            ignore_paths=["tmp"],
            wd=tmp_path,
        )
        assert not watcher._is_ignored(str(tmp_path / "tmpfile" / "out.txt"))

    def test_absolute_exclude_pattern(self, tmp_path):
        """An absolute exclude pattern matches the absolute path."""
        watcher = FileWatcher(
            watch_paths=["."],
            ignore_paths=[str(tmp_path / "_qk" / "tmp")],
            wd=tmp_path,
        )
        assert watcher._is_ignored(str(tmp_path / "_qk" / "tmp" / "out.txt"))
        assert not watcher._is_ignored(str(tmp_path / "_qk" / "tasks.py"))

    def test_ancestor_directories_are_not_matched(self, tmp_path):
        """Directories above the watch root never trigger an exclusion."""
        watched = tmp_path / "build" / "project"
        watched.mkdir(parents=True)
        watcher = FileWatcher(
            watch_paths=["."],
            ignore_paths=["build"],
            wd=watched,
        )
        assert not watcher._is_ignored(str(watched / "main.py"))

    def test_excluded_relative_to_innermost_watch_dir(self, tmp_path):
        """Anchored patterns apply to the watch root containing the path."""
        src = tmp_path / "src"
        (src / "tmp").mkdir(parents=True)
        watcher = FileWatcher(
            watch_paths=["src"],
            ignore_paths=["src/tmp"],
            wd=tmp_path,
        )
        assert watcher._is_ignored(str(src / "tmp" / "out.txt"))


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

    def test_resolve_absolute_path(self, tmp_path):
        """Absolute watch paths are used as-is, even outside the wd."""
        outside = tmp_path / "outside"
        outside.mkdir()
        watcher = FileWatcher(
            watch_paths=[str(outside)],
            wd=tmp_path / "inside",
        )
        assert watcher._resolve_watch_dirs() == [outside]

    def test_resolve_directory_paths(self, tmp_path):
        """Directory paths are resolved as observer roots."""
        (tmp_path / "pkg_a").mkdir()
        (tmp_path / "pkg_b").mkdir()
        watcher = FileWatcher(
            watch_paths=["pkg_a", "pkg_b"],
            wd=tmp_path,
        )
        dirs = watcher._resolve_watch_dirs()
        assert sorted(dirs) == [tmp_path / "pkg_a", tmp_path / "pkg_b"]

    def test_file_pattern_matches_only_matching_files(self, tmp_path):
        """File glob paths filter events while watching their parent."""
        matching = tmp_path / "match.py"
        other = tmp_path / "other.txt"
        matching.write_text("initial")
        other.write_text("initial")
        watcher = FileWatcher(["."], patterns=["*.py"], wd=tmp_path, debounce=0.0)
        watcher.start()
        try:
            time.sleep(0.1)
            watcher.reset()
            other.write_text("changed")
            time.sleep(0.1)
            assert not watcher.has_changes()
            matching.write_text("changed")
            time.sleep(0.1)
            assert watcher.has_changes()
        finally:
            watcher.stop()

    def test_patterns_filter_events_without_initial_matches(self, tmp_path):
        """Patterns filter events even when no matching file exists initially."""
        watcher = FileWatcher(["."], patterns=["*.py"], wd=tmp_path, debounce=0.0)
        assert watcher.watch_dirs == (tmp_path.resolve(),)

    def test_recursive_is_configurable(self, tmp_path):
        """Non-recursive watching ignores nested changes."""
        nested = tmp_path / "nested"
        nested.mkdir()
        watched = nested / "file.txt"
        watched.write_text("initial")
        watcher = FileWatcher(["."], wd=tmp_path, debounce=0.0, recursive=False)
        watcher.start()
        try:
            time.sleep(0.1)
            watched.write_text("changed")
            time.sleep(0.2)
            assert not watcher.has_changes()
        finally:
            watcher.stop()

    def test_watch_dirs_are_cached(self, tmp_path):
        """Resolved watch directories are computed once."""
        watcher = FileWatcher(watch_paths=["."], wd=tmp_path)
        assert watcher.watch_dirs is watcher.watch_dirs


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
            assert watcher.changed_paths() == [str(test_file)]

            watcher.reset()
            assert not watcher.has_changes()
            assert watcher.changed_paths() == []
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

    def test_wait_for_changes_waits_for_debounce(self, tmp_path):
        """Blocking waits return only after the debounce period."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("initial")
        watcher = FileWatcher(["."], wd=tmp_path, debounce=0.1)
        watcher.start()
        try:
            time.sleep(0.1)
            watcher.reset()
            test_file.write_text("modified")
            started = time.monotonic()
            assert watcher.wait_for_changes()
            minimum_wait = 0.05
            assert time.monotonic() - started >= minimum_wait
        finally:
            watcher.stop()

    def test_wait_for_changes_is_woken_by_stop(self, tmp_path):
        """Stopping a watcher wakes a blocked wait."""
        watcher = FileWatcher(["."], wd=tmp_path)
        result = []
        waiting = threading.Thread(
            target=lambda: result.append(watcher.wait_for_changes())
        )
        waiting.start()
        time.sleep(0.05)
        watcher.stop()
        waiting.join(timeout=1)
        assert not waiting.is_alive()
        assert result == [False]


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

    def test_watch_paths_split_by_cli(self):
        """Semicolon-separated watch paths remain one parser value."""
        parser = AppArgumentParser()
        namespace, _ = parser.parse_known_args(
            ["--watch", "--watch-paths", "src;*.py", "my-task"]
        )
        assert namespace.watch_paths == ["src;*.py"]

    def test_watch_recursive_parsed(self):
        """--watch-recursive enables recursive watching."""
        parser = AppArgumentParser()
        namespace, _ = parser.parse_known_args(
            ["--watch", "--watch-recursive", "my-task"]
        )
        assert namespace.watch_recursive is True

    def test_watch_ignore_options_parsed(self):
        """Watch ignore paths and patterns are parsed as lists."""
        parser = AppArgumentParser()
        namespace, _ = parser.parse_known_args(
            [
                "--watch",
                "--watch-ignore-paths",
                "build/",
                "--watch-ignore-patterns",
                "*.pyc;*.pyo",
                "my-task",
            ]
        )
        assert namespace.watch_ignore_paths == ["build/"]
        assert namespace.watch_ignore_patterns == ["*.pyc;*.pyo"]

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

    def test_watch_defaults_are_none(self):
        """--watch-debounce defaults to None."""
        parser = AppArgumentParser()
        namespace, _ = parser.parse_known_args(["--watch", "my-task"])
        assert namespace.watch_debounce is None
