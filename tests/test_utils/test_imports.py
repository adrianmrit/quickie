from pathlib import Path

from quickie import constants


def test_import_from_path():
    from quickie.utils.imports import import_from_path

    root = Path.cwd()
    path = root / constants.TASKS_PATH
    module = import_from_path(path)
    assert module.__name__ == constants.TASKS_PATH.stem
