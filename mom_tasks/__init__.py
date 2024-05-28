from task_mom import tasks

from . import tests

MOM_NAMESPACES = {
    "tests": tests,
}


class HelloWorld(tasks.Task):
    """Hello world task."""

    class Meta:
        alias = "hello"

    def run(self, **kwargs):
        self.confirm("[info]Are you ready?[/info]")
        self.print_info("Hello world!")
