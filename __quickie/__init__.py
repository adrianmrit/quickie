from quickie import script, task, Namespace
from quickie import console
from quickie.errors import Skip, Stop

from . import install, test

_ = Namespace(
    {
        "": [install, test],
        "test": test,
        "install": install,
    }
)


def print_name():
    print(__name__)
    print(__file__)


@task
def hello():
    console.print("Hello world!")
    console.print_info("This is an info message.")
    console.print_error("This is an error message.")
    console.print_warning("This is a warning message.")
    console.print_success("This is a success message.")


@script(
    env={"OTHER": "Other"},
    bind=True,
)
def script_example(task):
    """Example script that runs a command."""
    return """
    echo $MY_VAR $OTHER
    """


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


@task
def skip_example():
    """Example task that skips."""
    console.print("This task will be skipped.")
    raise Skip("Skipping this task.")


@task
def stop_example():
    """Example task that stops all tasks."""
    console.print("This task will stop all tasks.")
    raise Stop("Stopping all tasks.")
