from pathlib import Path

import pytest


def test_import_from_path():
    from quickie.utils.imports import import_from_path

    root = Path.cwd()
    path = root / "tests/_qk_test"
    module = import_from_path(path)
    assert module.__name__ == "_qk_test"


def test_import_python_file(tmp_path):
    from quickie.utils.imports import import_from_path

    py_file = tmp_path / "my_module.py"
    py_file.write_text("VALUE = 42")

    module = import_from_path(py_file)
    assert module.__name__ == "my_module"
    assert module.VALUE == 42  # type: ignore[attr-defined]


def test_import_invalid_path():
    from quickie.utils.imports import InternalImportError, import_from_path

    with pytest.raises(InternalImportError, match="not a valid module"):
        import_from_path("/nonexistent/path/does_not_exist")


def test_import_broken_module(tmp_path):
    from quickie.utils.imports import InternalImportError, import_from_path

    py_file = tmp_path / "broken.py"
    py_file.write_text("from nonexistent_package_xyz_abc import something")

    with pytest.raises(InternalImportError, match="Could not import"):
        import_from_path(py_file)
