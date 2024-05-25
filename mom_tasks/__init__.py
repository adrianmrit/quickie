from task_mom import tasks

from . import tests

MOM_NAMESPACES = {
    "tests": tests,
}


class HelloWorld(tasks.Task):
    """Hello world task."""

    alias = "hello"

    def run(self, **kwargs):
        print("Hello world!")
