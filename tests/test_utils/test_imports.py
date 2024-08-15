from pathlib import Path


def test_import_from_path():
    from quickie.utils.imports import import_from_path

    root = Path.cwd()
    path = root / "tests/__quickie_test"
    module = import_from_path(path)
    assert module.__name__ == "__quickie_test"
