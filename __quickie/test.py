from quickie import command, script


@command(extra_args=True)
def test(*args):
    """Run tests."""
    return ["python", "-m", "pytest", *args]


@script
def coverage():
    """Run tests with coverage."""
    return """
    coverage run -m pytest
    coverage html
    """
