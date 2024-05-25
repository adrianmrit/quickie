from pathlib import Path


def test_import_from_path():
    from task_mom.utils.imports import import_from_path

    root = Path.cwd()
    path = root / "mom_tasks"
    module = import_from_path(path)
    assert module.__name__ == "mom_tasks"
