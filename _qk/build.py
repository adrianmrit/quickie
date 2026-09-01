from quickie import script, console, app


@script
def build():
    """Build the package using the Python build module."""
    return """
    uv run python -m build
    """


@script(
    extra_args=True,
    after=[
        lambda: console.print_info(
            f"[link=file://{app.context.wd}/docs/build/html/index.html]docs/build/html/index.html[/link]"
        )
    ],
)
def docs(*args):
    """Builds the sphinx documentation."""
    args = " ".join(args)
    return f"""
    rm -rf docs/build
    rm -rf docs/source/generated
    uv run sphinx-build -M html docs/source docs/build {args}
    """
