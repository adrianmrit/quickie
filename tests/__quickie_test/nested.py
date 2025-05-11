from quickie import tasks, app, task


@task(name="other")
class Other(tasks.Script):
    """Other task."""

    extra_args = True

    def get_script(self, *args) -> str:
        args = " ".join(args)
        script = f"echo {args}"
        app.console.print(f"Running: {script}")
        return script
