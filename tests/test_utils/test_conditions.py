from pathlib import Path
import pytest

from quickie.conditions import FilesModified, FirstRun, PathsExist
from quickie.factories import task


class TestFilesModified:
    @pytest.mark.parametrize("algorithm", FilesModified.Algorithm)
    def test(self, tmpdir, algorithm):
        @task
        def my_task():
            pass

        file1 = tmpdir.join("file1")
        file1.write("content")
        directory = tmpdir.mkdir("directory")
        file2 = directory.join("file2")
        file2.write("other content")
        condition = FilesModified([file1, directory], algorithm=algorithm)
        assert condition(my_task)
        assert not condition(my_task)
        file1.write("new content")
        assert condition(my_task)
        assert not condition(my_task)

        # condition with missing files
        missing_file = directory.join("missing")
        missing_file.write("missing content")
        condition = FilesModified(
            [file1, directory, missing_file], algorithm=algorithm, allow_missing=False
        )
        assert condition(my_task)
        # Delete the missing file to test the cache
        missing_file.remove()
        assert condition(
            my_task
        )  # second call should be true since allow_missing is False
        assert condition(my_task)  # While file is missing the condition will pass
        missing_file.write("missing content")
        assert condition(
            my_task
        )  # file is back, but files still changed, so condition holds
        assert not condition(my_task)  # nothing changed, so condition is false

        # condition with missing files
        condition = FilesModified(
            [file1, directory, missing_file], algorithm=algorithm, allow_missing=True
        )
        assert condition(my_task)  # params changed, so cache is invalidated
        # Delete the missing file to test the cache
        missing_file.remove()
        assert not condition(my_task)  # File is missing but otherwise nothing changed

        # condition with excluded files
        file1.write("content again")
        file3 = directory.join("file3")
        file3.write("other content")
        condition = FilesModified(
            [file1, directory], exclude=[Path(file3)], algorithm=algorithm
        )
        assert condition(my_task)
        file3.write("new content")
        assert not condition(my_task)
        condition = FilesModified([file1, directory], algorithm=algorithm)
        assert condition(my_task)


class TestPathsExist:
    def test(self, tmpdir):
        @task
        def my_task():
            pass

        file1 = tmpdir.join("file1")
        file1.write("content")
        directory = tmpdir.mkdir("directory")
        file2 = directory.join("file2")
        file2.write("other content")
        condition = PathsExist(file1, file2)
        t = my_task()
        assert condition(t)
        file1.remove()
        assert not condition(t)
        file1.write("new content")
        assert condition(t)
        file1.remove()
        assert not condition(t)


class TestFirstRun:
    def test(self):
        @task
        def my_task(*args):
            pass

        condition = FirstRun()
        t = my_task()
        assert condition(t)
        assert not condition(t)
        assert not condition(t, "value1", "value2")

    def test_check_args(self):
        @task
        def my_task(*args):
            pass

        condition = FirstRun(check_args=True)
        t = my_task()
        assert condition(t, "value1", "value2")
        assert not condition(t, "value1", "value2")
        assert condition(t, "value1", "value3")
        assert not condition(t, "value1", "value3")
        assert condition(t)
        assert not condition(t)
