from pathlib import Path


def test_import_from_path():
    from task_mom.utils.imports import import_from_path

    root = Path.cwd()
    path = root / "__mom__"
    module = import_from_path(path)
    assert module.__name__ == "__mom__"
