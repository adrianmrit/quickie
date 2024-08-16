from quickie import Task, script, task

from . import install, test

QCK_NAMESPACES = {
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
