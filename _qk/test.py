import shlex

from quickie import command, script


@command(extra_args=True)
def test(*args):
    """Run tests."""
    return ["python", "-m", "pytest", *args]


@script(extra_args=True)
def test_matrix(*args):
    """Run tests with Python 3.12, 3.13, and 3.14 via uv."""
    pytest_args = shlex.join(args)
    commands = [
        f"uv run --python {version} python -m pytest {pytest_args}".rstrip()
        for version in ("3.12", "3.13", "3.14")
    ]
    return "set -e\n" + "\n".join(commands)


@script
def coverage():
    """Run tests with coverage."""
    return """
    source .venv/bin/activate
    coverage run -m pytest
    coverage html
    """
