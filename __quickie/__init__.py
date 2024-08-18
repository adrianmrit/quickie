from quickie import Task, script, task

from . import install, test

NAMESPACES = {
    "": test,
    "test": test,
    "install": install,
}


@task(bind=True)
def hello(self: Task):
    self.print("Hello world!")
    self.print_info("This is an info message.")
    self.print_error("This is an error message.")
    self.print_warning("This is a warning message.")
    self.print_success("This is a success message.")


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
            lambda self: self.print_info(
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
