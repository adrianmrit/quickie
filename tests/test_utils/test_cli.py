import io

import pytest
from quickie.utils.console import QkConsole


class TestQkConsole:
    @pytest.fixture
    def console(self):
        console = QkConsole(force_terminal=True)
        console.file = io.StringIO()
        return console

    def test_print(self, console: QkConsole):
        console.print("Hello world!")

        console.file.seek(0)
        assert console.file.read() == "Hello world!\n"

    def test_print_error(self, console: QkConsole):
        console.print_error("Hello world!")

        console.file.seek(0)
        out = console.file.read()
        assert "Hello world!" in out
        assert out.endswith("\n")
        assert "\x1b" in out

    def test_print_info(self, console):
        console.print_info("Hello world!")

        console.file.seek(0)
        out = console.file.read()
        assert "Hello world!" in out
        assert out.endswith("\n")
        assert "\x1b" in out

    def test_print_success(self, console):
        console.print_success("Hello world!")

        console.file.seek(0)
        out = console.file.read()
        assert "Hello world!" in out
        assert out.endswith("\n")
        assert "\x1b" in out

    def test_print_warning(self, console):
        console.print_warning("Hello world!")

        console.file.seek(0)
        out = console.file.read()
        assert "Hello world!" in out
        assert out.endswith("\n")
        assert "\x1b" in out

    def test_prompt(self, mocker, console):
        mocker.patch("quickie.utils.console.Prompt.ask", return_value="yes")
        assert console.prompt("Prompt") == "yes"

    def test_confirm(self, mocker, console):
        mocker.patch("quickie.utils.console.Confirm.ask", return_value=True)
        assert console.confirm("Prompt") is True
