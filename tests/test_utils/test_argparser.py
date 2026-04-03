import argparse
from unittest.mock import MagicMock


from quickie.utils.argparser import Arg, _get_default_completer


def test_default_completer_with_choices():
    action = MagicMock()
    action.choices = ["a", "b"]
    action.type = str
    assert _get_default_completer(action) is None


def test_default_completer_with_non_string_type():
    action = MagicMock()
    action.choices = None
    action.type = int
    assert _get_default_completer(action) is None


def test_default_completer_str_type():
    from argcomplete.completers import FilesCompleter

    action = MagicMock()
    action.choices = None
    action.type = str
    result = _get_default_completer(action)
    assert isinstance(result, FilesCompleter)


def test_arg_with_custom_completer():
    custom_completer = MagicMock()
    arg = Arg("--myarg", completer=custom_completer)
    parser = argparse.ArgumentParser()
    action = arg.add(parser)
    assert action.completer is custom_completer


def test_arg_without_completer_gets_default():
    from argcomplete.completers import FilesCompleter

    arg = Arg("--myarg")
    parser = argparse.ArgumentParser()
    action = arg.add(parser)
    assert isinstance(action.completer, FilesCompleter)


def test_arg_with_choices_no_completer():
    arg = Arg("--myarg", choices=["x", "y"])
    parser = argparse.ArgumentParser()
    action = arg.add(parser)
    assert not hasattr(action, "completer")
