import pytest

from quickie.conditions import FilesModified, FirstRun, PathsExist
from quickie.factories import task


class TestFilesNotModified:
    @pytest.mark.parametrize("algorithm", FilesModified.Algorithm)
    def test(self, tmpdir, context, algorithm):
        @task
        def my_task():
            pass

        file1 = tmpdir.join("file1")
        file1.write("content")
        directory = tmpdir.mkdir("directory")
        file2 = directory.join("file2")
        file2.write("other content")
        condition = FilesModified([file1, directory], algorithm=algorithm)
        t = my_task(context=context)
        assert condition(t)
        assert not condition(t)
        file1.write("new content")
        assert condition(t)
        assert not condition(t)

        # condition with missing files
        missing_file = directory.join("missing")
        condition = FilesModified(
            [file1, directory, missing_file], algorithm=algorithm, allow_missing=False
        )
        assert condition(t)
        condition = FilesModified(
            [file1, directory, missing_file], algorithm=algorithm, allow_missing=True
        )
        assert not condition(t)

        # condition with excluded files
        file1.write("content again")
        file3 = directory.join("file3")
        file3.write("other content")
        condition = FilesModified(
            [file1, directory], exclude=[file3], algorithm=algorithm
        )
        assert condition(t)
        file3.write("new content")
        assert not condition(t)
        condition = FilesModified([file1, directory], algorithm=algorithm)
        assert condition(t)


class TestPathsExist:
    def test(self, tmpdir, context):
        @task
        def my_task():
            pass

        file1 = tmpdir.join("file1")
        file1.write("content")
        directory = tmpdir.mkdir("directory")
        file2 = directory.join("file2")
        file2.write("other content")
        condition = PathsExist(file1, file2)
        t = my_task(context=context)
        assert condition(t)
        file1.remove()
        assert not condition(t)
        file1.write("new content")
        assert condition(t)
        file1.remove()
        assert not condition(t)


class TestFirstRun:
    def test(self, context):
        @task
        def my_task(*args):
            pass

        condition = FirstRun()
        t = my_task(context=context)
        assert condition(t)
        assert not condition(t)
        assert not condition(t, "value1", "value2")

    def test_check_args(self, context):
        @task
        def my_task(*args):
            pass

        condition = FirstRun(check_args=True)
        t = my_task(context=context)
        assert condition(t, "value1", "value2")
        assert not condition(t, "value1", "value2")
        assert condition(t, "value1", "value3")
        assert not condition(t, "value1", "value3")
        assert condition(t)
        assert not condition(t)
