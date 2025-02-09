from quickie import script, task, Namespace
from quickie import console

from . import install, test

namespace = Namespace(
    {
        "": [install, test],
        "test": test,
        "install": install,
    }
)


@task
def hello():
    console.print("Hello world!")
    console.print_info("This is an info message.")
    console.print_error("This is an error message.")
    console.print_warning("This is a warning message.")
    console.print_success("This is a success message.")


@script
def build():
    return """
    python -m build
    python -m build src/quickie_global -o dist
    """


@script
def upload():
    return """
    python -m twine upload dist/*
    """


@script(
    extra_args=True,
    after=[
        task(bind=True)(
            lambda self: console.print_info(
                f"[link=file://{self.context.cwd}/docs/build/html/index.html]docs/build/html/index.html[/link]"
            )
        )
    ],
)
def build_docs(*args):
    """Builds the sphinx documentation."""
    args = " ".join(args)
    return f"""
    rm -rf docs/build
    rm -rf docs/source/generated
    sphinx-build -M html docs/source docs/build {args}
    """
