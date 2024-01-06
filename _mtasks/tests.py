from task_mom import tasks

tests_namespace = tasks.Namespace("tests")


@tasks.register
@tests_namespace.register
class Test(tasks.ScriptTask):
    """Test task."""

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("extra", nargs="*")

    def get_script(self, extra) -> str:
        return f"python -m pytest {extra}"
