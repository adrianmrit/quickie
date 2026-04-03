from pathlib import Path
import pytest

from quickie.conditions import All, FilesModified, FirstRun, PathsExist, condition
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
        condition = FilesModified(
            "identifier1", paths=[file1, directory], algorithm=algorithm
        )
        assert condition(my_task)
        assert not condition(my_task)
        file1.write("new content")
        assert condition(my_task)
        assert not condition(my_task)

        # condition with missing files
        missing_file = directory.join("missing")
        missing_file.write("missing content")
        condition = FilesModified(
            "identifier2",
            paths=[file1, directory, missing_file],
            algorithm=algorithm,
            allow_missing=False,
        )
        assert condition(my_task)
        # Delete the missing file to test the cache
        missing_file.remove()
        assert condition(my_task)
        # second call should return false since even though the file is missing,
        # that didn't change from the previous call
        assert not condition(my_task)

        # File is back, so something changed
        missing_file.write("missing content")
        assert condition(my_task)
        assert not condition(my_task)  # nothing changed, so condition is false

        # condition with missing files
        condition = FilesModified(
            "identifier3",
            paths=[file1, directory, missing_file],
            algorithm=algorithm,
            allow_missing=True,
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
            "identifier4",
            paths=[file1, directory],
            exclude=[Path(file3)],
            algorithm=algorithm,
        )
        assert condition(my_task)
        file3.write("new content")
        assert not condition(my_task)
        condition = FilesModified(
            "identifier5", paths=[file1, directory], algorithm=algorithm
        )
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


class TestAll:
    def test_all_true(self):
        c1 = condition(lambda task, *a, **k: True)
        c2 = condition(lambda task, *a, **k: True)
        assert All(c1, c2)(None)

    def test_one_false(self):
        c1 = condition(lambda task, *a, **k: True)
        c2 = condition(lambda task, *a, **k: False)
        assert not All(c1, c2)(None)

    def test_all_false(self):
        c1 = condition(lambda task, *a, **k: False)
        c2 = condition(lambda task, *a, **k: False)
        assert not All(c1, c2)(None)

    def test_empty_is_true(self):
        assert All()(None)


class TestConditionRepr:
    def test_base_repr(self):
        def my_cond(task, *args, **kwargs):
            return True

        c = condition(my_cond)
        assert repr(c) == "my_cond()"

    def test_and_repr(self):
        def cond1(task, *a, **k):
            return True

        def cond2(task, *a, **k):
            return True

        c1 = condition(cond1)
        c2 = condition(cond2)
        assert repr(c1 & c2) == "cond1() & cond2()"

    def test_or_repr(self):
        def cond1(task, *a, **k):
            return True

        def cond2(task, *a, **k):
            return True

        c1 = condition(cond1)
        c2 = condition(cond2)
        assert repr(c1 | c2) == "cond1() | cond2()"

    def test_not_repr(self):
        def cond1(task, *a, **k):
            return True

        c1 = condition(cond1)
        assert repr(~c1) == "~cond1()"

    def test_xor_repr(self):
        def cond1(task, *a, **k):
            return True

        def cond2(task, *a, **k):
            return False

        c1 = condition(cond1)
        c2 = condition(cond2)
        assert repr(c1 ^ c2) == "cond1() ^ cond2()"


class TestShortCircuit:
    def test_and_does_not_evaluate_second_when_first_false(self):
        calls = []

        def cond1(task, *a, **k):
            calls.append("c1")
            return False

        def cond2(task, *a, **k):
            calls.append("c2")
            return True

        result = (condition(cond1) & condition(cond2))(None)
        assert not result
        assert calls == ["c1"]

    def test_or_does_not_evaluate_second_when_first_true(self):
        calls = []

        def cond1(task, *a, **k):
            calls.append("c1")
            return True

        def cond2(task, *a, **k):
            calls.append("c2")
            return False

        result = (condition(cond1) | condition(cond2))(None)
        assert result
        assert calls == ["c1"]
