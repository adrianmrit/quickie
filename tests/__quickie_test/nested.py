from quickie import tasks, console


class Other(tasks.Script, name="other"):
    """Other task."""

    extra_args = True

    def get_script(self, *args) -> str:
        args = " ".join(args)
        script = f"echo {args}"
        console.print(f"Running: {script}")
        return script
