import json
import shlex
import sys

from quickie import script, task, command, OutputMode
from quickie import console
from quickie.errors import Skip, Stop
from quickie.utils.argparser import Arg


@task(
    args=[
        Arg("--name", required=True),
    ],
    watch_paths=["./src/quickie"],
)
def hello(name):
    console.print(f"Hello {name}!")
    console.print_info("This is an info message.")
    console.print_error("This is an error message.")
    console.print_warning("This is a warning message.")
    console.print_success("This is a success message.")


@task(
    args=[
        Arg("target"),
        Arg("--name", "-n", default="world"),
        Arg("--count", "-c", type=int, default=1),
        Arg("--tag", dest="tags", action="append", default=[]),
        Arg("--loud", action="store_true"),
        Arg("--mode", choices=["safe", "fast"], default="safe"),
        Arg("--paths"),
    ],
    extra_args=True,
)
def arguments_example(*extra, **options):
    """Print parsed options and extra arguments as JSON."""
    print(json.dumps({**options, "extra": extra}))


def _extra_command(extra, name):
    return [
        sys.executable,
        "-c",
        "import json, sys; "
        "print(json.dumps({'name': sys.argv[1], 'extra': sys.argv[2:]}))",
        name,
        *extra,
    ]


@command(args=[Arg("--name", "-n", default="world")], extra_args=True)
def extra_command_example(*extra, name):
    """Forward extra arguments to a Python subprocess and print its JSON."""
    return _extra_command(extra, name)


@script(args=[Arg("--name", "-n", default="world")], extra_args=True)
def extra_script_example(*extra, name):
    """Forward extra arguments through a shell with safe quoting."""
    return shlex.join(_extra_command(extra, name))


@script(env={"OTHER": "Other"}, bind=True, wd=".", watch_paths=["./src/quickie"])
def script_example(task):
    """Example script that runs a command."""
    return """
    echo $MY_VAR $OTHER
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


# ── output_mode examples ──────────────────────────────────────────────────────


@script(output_mode=OutputMode.CAPTURE)
def capture_example():
    """Capture stdout/stderr without printing to the terminal.

    Demonstrates OutputMode.CAPTURE: result.stdout is available, nothing
    is written to the terminal during execution.
    """
    return "echo 'captured output'; echo 'captured stderr' >&2"


@task
def show_captured():
    """Run capture_example and print the captured bytes afterwards."""
    result = capture_example()
    console.print(f"[bold]stdout:[/bold] {result.stdout!r}")
    console.print(f"[bold]stderr:[/bold] {result.stderr!r}")


@script(output_mode=OutputMode.TEE)
def tee_example():
    """Stream output to the terminal AND capture it.

    Demonstrates OutputMode.TEE: you should see output live, and the
    captured bytes are also available on the returned CompletedProcess.
    """
    return "echo 'tee stdout'; echo 'tee stderr' >&2"


@task
def show_tee():
    """Run tee_example, then echo the captured bytes to confirm TEE worked."""
    result = tee_example()
    console.print(f"[bold]captured stdout:[/bold] {result.stdout!r}")
    console.print(f"[bold]captured stderr:[/bold] {result.stderr!r}")


@command(output_mode="capture")
def capture_command_example():
    """Same as capture_example but using a command task and a string literal mode."""
    return ["echo", "command captured"]


@task
def show_captured_command():
    """Run capture_command_example and show the captured bytes."""
    result = capture_command_example()
    console.print(f"[bold]stdout:[/bold] {result.stdout!r}")
