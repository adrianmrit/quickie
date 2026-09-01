from quickie import script, task, command, namespace
from quickie.utils.argparser import Arg


@namespace
def _():
    from . import install, test, build  # noqa: PLC0415

    return [install, test.test, build.build]


@namespace(path="install")
def install_n():
    from . import install  # noqa: PLC0415

    return install


@namespace(path="build")
def build_n():
    from . import build  # noqa: PLC0415

    return build


@namespace(path="test")
def test_n():
    from . import test  # noqa: PLC0415

    return test


@namespace(path="examples")
def examples_n():
    from . import examples  # noqa: PLC0415

    return examples


@script
def upload():
    """Upload the package to PyPI using Twine."""
    return """
    uv run python -m twine upload dist/*
    """


@command(private=True)
def _ensure_no_unstaged_changes():
    return "git diff --quiet"


@task(private=True)
def _pre_release_checks(version):
    from quickie._meta import __version__

    assert __version__ == version, f"Version mismatch: {__version__} != {version}"

    # Check that the changelog has an entry for the version
    changelog_path = "CHANGELOG.md"
    with open(changelog_path) as f:
        changelog = f.read()
    assert f"## Release {version}" in changelog, (
        f"Changelog does not have an entry for version {version}"
    )


@script(private=True)
def _commit_release(message, version):
    """Release a new version."""
    # Check version matches the version in _meta.py

    return f"""
    git commit -m "{message}"
    git tag {version}
    git push origin main --tags
    """


def _build():
    from .build import build

    return build()


def _build_docs():
    from .build import docs

    return docs()


@task(
    args=[
        Arg("-m", "--message", help="Commit message", required=True),
        Arg("-v", "--version", help="Version to release", required=True),
    ],
    before=[
        _ensure_no_unstaged_changes,
        _build,
        _build_docs,
        _ensure_no_unstaged_changes,
    ],
    after=[
        upload,
    ],
)
def release(version, message):
    """Release a new version."""
    _pre_release_checks(version)
    _ensure_no_unstaged_changes()
    _build_docs()
    # Again, to manually inspect the docs changes if anything new was generated.
    _ensure_no_unstaged_changes()
    _commit_release(message, version)
    # Again, pre-commit might have made changes
    _ensure_no_unstaged_changes()
    # Finally, upload the package to PyPI
    upload()
