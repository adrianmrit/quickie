"""The CLI entry of task-mom."""
from argparse import ArgumentParser

from ._version import __version__ as version


def main(argv=None):
    """A CLI tool that does your chores while you slack off."""
    parser = ArgumentParser()
    parser.description = main.__doc__
    parser.add_argument("-p", "--print", action="store_true", help="print hello world")
    parser.add_argument("-V", "--version", action="version", version=version)
    args = parser.parse_args(argv)
    if args.print:
        print("Hello world!")
