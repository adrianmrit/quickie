from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "path,root,expected",
    (
        (Path("foo/bar.py"), Path("/foo"), "foo.bar"),
        (Path("foo/bar"), Path("/foo/"), "foo.bar"),
        (Path("foo/bar.py"), Path("/some other path/"), "foo.bar"),
        (Path("/foo/bar"), Path("/some other path/"), "foo.bar"),
        (Path("/foo/bar/__init__.py"), Path("/some other path/"), "foo.bar"),
        (Path("/foo/bar/__init__"), Path("/foo/"), "bar"),
    ),
)
def test_module_name_from_path(path, root, expected):
    from task_mom.utils.imports import module_name_from_path

    assert module_name_from_path(path, root=root) == expected


def test_import_from_path():
    from task_mom.utils.imports import import_from_path

    root = Path.cwd()
    path = root / "_mtasks"
    module = import_from_path(path, root=root)
    assert module.__name__ == "_mtasks"


@pytest.mark.parametrize(
    "module,works",
    (
        ("task_mom.utils.imports", True),
        ("task_mom.utils.imports.does_not_exist", False),
        ("..utils.imports", False),
    ),
)
def test_try_import(module, works):
    from task_mom.utils.imports import try_import

    result = try_import(module)
    if works:
        assert result is not None
    else:
        assert result is None
