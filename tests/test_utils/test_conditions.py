import pytest

from quickie.factories import task
from quickie.utils.conditions import FilesNotModified, PathsExist


class TestFilesNotModified:
    @pytest.mark.parametrize("algorithm", FilesNotModified.Algorithm)
    def test(self, tmpdir, context, algorithm):
        @task
        def my_task():
            pass

        file1 = tmpdir.join("file1")
        file1.write("content")
        directory = tmpdir.mkdir("directory")
        file2 = directory.join("file2")
        file2.write("other content")
        condition = FilesNotModified(file1, file2, algorithm=algorithm)
        t = my_task(context=context)
        assert not condition(t)
        assert condition(t)
        file1.write("new content")
        assert not condition(t)
        assert condition(t)

        # condition with missing files
        missing_file = tmpdir.join("missing")
        condition = FilesNotModified(
            file1, file2, missing_file, algorithm=algorithm, allow_missing=False
        )
        assert not condition(t)
        condition = FilesNotModified(
            file1, file2, missing_file, algorithm=algorithm, allow_missing=True
        )
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
