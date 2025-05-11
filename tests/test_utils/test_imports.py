from pathlib import Path


def test_import_from_path():
    from quickie.utils.imports import import_from_path

    root = Path.cwd()
    path = root / "tests/_qk_test"
    module = import_from_path(path)
    assert module.__name__ == "_qk_test"
