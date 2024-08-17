#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
"""Entry point for the application script."""


import sys

from ._cli import main


def _run_main():
    if __name__ == "__main__":
        argv = sys.argv[1:]
        main(argv)


_run_main()
