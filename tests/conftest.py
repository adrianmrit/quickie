import os

import pytest
from frozendict import frozendict
from rich.console import Console
from rich.theme import Theme

from task_mom import settings
from task_mom.context import Context

DEFAULT_CONSOLE_THEME = Theme(settings.DEFAULT_CONSOLE_STYLE)


@pytest.fixture
def context():
    return Context(
        program_name="mom",
        cwd=os.getcwd(),
        env=frozendict(os.environ),
        console=Console(theme=DEFAULT_CONSOLE_THEME),
    )
