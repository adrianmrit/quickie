from task_mom import tasks

from . import tests
from .tests import Test  # noqa: F401

MOM_NAMESPACES = {
    "tests": tests,
}


class HelloWorld(tasks.Task):
    """Hello world task."""

    class Meta:
        alias = "hello"

    def run(self, **kwargs):
        self.print("Hello world!")
        self.print_info("This is an info message.")
        self.print_error("This is an error message.")
        self.print_warning("This is a warning message.")
        self.print_success("This is a success message.")


class InstallLocal(tasks.ScriptTask):
    class Meta:
        alias = "install.local"

    script = """
    pipx install . --force
    rm -rf build
    rm -rf src/task_mom.egg-info
    """
