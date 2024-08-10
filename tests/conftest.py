import os
from pathlib import Path

import pytest
from frozendict import frozendict
from pytest import MonkeyPatch
from rich.console import Console
from rich.theme import Theme

from quickie import constants
from quickie.context import Context

DEFAULT_CONSOLE_THEME = Theme(constants.DEFAULT_CONSOLE_STYLE)


@pytest.fixture(autouse=True, scope="session")
def patch_constants():
    m = MonkeyPatch()
    m.setattr("quickie.constants.TASKS_PATH", Path("tests/__quickie_test"))
    m.setattr("quickie.constants.HOME_PATH", Path("tests/__home_test__"))
    m.setattr(
        "quickie.constants.SETTINGS_PATH", Path("tests/__home_test__/settings.toml")
    )


@pytest.fixture
def context():
    return Context(
        program_name="qck",
        cwd=os.getcwd(),
        env=frozendict(os.environ),
        console=Console(theme=DEFAULT_CONSOLE_THEME),
    )
