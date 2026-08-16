from pathlib import Path

import pytest

from quickie._namespace import RootNamespace


@pytest.fixture(autouse=True)
def patch_config(tmpdir_factory, mocker):
    """Patch the config module to use a temporary directory for the home path."""
    # Prevent the launcher from firing (and calling os.execv) in unit tests.
    mocker.patch.dict("os.environ", {"QK_LAUNCHER_RUNNING": "true"})

    # Patch the configure method
    mocker.patch("quickie.app._home_path", Path("tests/_qk_home"), create=True)
    mocker.patch("quickie.app._project_path", Path("tests/_qk_test"), create=True)
    mocker.patch(
        "quickie.app._tmp_relative_path",
        Path(tmpdir_factory.mktemp("quickie_tmp")),
        create=True,
    )

    # Reset the namespace every time
    mocker.patch("quickie.app._tasks", RootNamespace(), create=True)
    mocker.patch("quickie.app.program_name", "qk")
    mocker.patch("quickie.app._cached_task_names", None, create=True)
