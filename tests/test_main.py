"""Tests for the ``quickie.__main__`` module.

The module is a thin wrapper around ``quickie._cli.main`` that is executed
when the package is run with ``python -m quickie``. Importing the module
runs ``_run_main()`` at module level, but the ``if __name__ == "__main__"``
guard is skipped because ``__name__`` is not ``"__main__"`` when imported.
"""

import quickie.__main__ as quickie_main


def test_run_main_forwards_argv_to_cli_main(mocker):
    """``_run_main()`` forwards ``sys.argv[1:]`` to ``quickie._cli.main``."""
    # ``__main__`` does ``from ._cli import main``, so patch the reference
    # already bound on the module rather than ``quickie._cli.main``.
    mock_main = mocker.patch.object(quickie_main, "main")
    mocker.patch("sys.argv", ["quickie", "hello", "--flag"])
    # Simulate execution as ``python -m quickie`` so the guard body runs.
    mocker.patch.object(quickie_main, "__name__", "__main__")

    quickie_main._run_main()

    mock_main.assert_called_once_with(["hello", "--flag"])
