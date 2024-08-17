import os

import pytest
from frozendict import frozendict
from pytest import MonkeyPatch
from rich.console import Console
from rich.theme import Theme

from quickie import _cli, config
from quickie._namespace import RootNamespace
from quickie.context import Context

DEFAULT_CONSOLE_THEME = Theme(config.CONSOLE_STYLE)


@pytest.fixture(autouse=True, scope="session")
def patch_config(tmpdir_factory):
    m = MonkeyPatch()
    original = _cli.Main.get_config

    def new_get_config(self, **kwargs):
        # Values can be set and be null or empty string, in which case we
        # want to override the default.
        kwargs["home_path"] = kwargs.get("home_path") or "tests/__quickie_home"
        kwargs["tasks_module_name"] = (
            kwargs.get("tasks_module_name") or "tests/__quickie_test"
        )
        kwargs["tmp_relative_path"] = kwargs.get("tmp_relative_path") or str(
            tmpdir_factory.mktemp("quickie_tmp")
        )
        return original(self, **kwargs)

    m.setattr(_cli.Main, "get_config", new_get_config)


@pytest.fixture
def context(tmpdir):
    return Context(
        program_name="qck",
        cwd=os.getcwd(),
        env=frozendict(os.environ),
        console=Console(theme=DEFAULT_CONSOLE_THEME),
        namespace=RootNamespace(),
        config=config.CliConfig(
            home_path="tests/__quickie_home",
            tasks_module_name="tests/__quickie_test",
            tmp_relative_path=str(tmpdir),
            use_global=False,
        ),
    )
