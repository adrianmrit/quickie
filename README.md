# Quickie - A CLI tool for quick tasks

[![License](https://img.shields.io/github/license/adrianmrit/quickie)](https://github.com/adrianmrit/quickie/blob/master/LICENSE)

## Getting Started

### Installing

Quickie can be installed either on a per-project basis and globally.

For projects it is recommended to use a virtual environment and install via `pip`:

```sh
python -m venv .venv
source .venv/bin/activate
pip install quickie-runner
qck --help
```

For global installation, you can install `quickie-runner-global` instead. It will add
`quickie-runner` as a dependency, but also add a `qckg` executable, which will run global
tasks by default. This allows us to run our global tasks from any project without conflicts.

For global installation it is recommended to use `pipx`, as it will install it in an isolated
environment:

```sh
pipx install quickie-runner-global
qckg --help
```

If you have any issues with the `quickie` package missing when running `qckg`, you can inject it manually:

```sh
pipx inject quickie-runner-global quickie-runner
```

See the [pipx](https://pipx.pypa.io/stable/)

## Tab completion

Tab completion is available for bash and zsh. It depends on the `argcomplete` package, which should have been installed with `quickie`.

To enable tab completion for `quickie`, add the following line to your `.bashrc` or `.zshrc`:

```sh
eval "$(register-python-argcomplete qck)"
eval "$(register-python-argcomplete qckg)"
```

If you get the following error in the zsh shell:

```sh
complete:13: command not found: compdef
```

You can fix it by adding the following line to your `.zshrc` (before the line that registers the completion):

```sh
autoload -Uz compinit && compinit
```

## Usage

Per-project tasks are configured under a `__quickie.py` or `__quickie` python module in the current directory.
If using a `__quickie` directory, the tasks should be defined in the `__quickie/__init__.py` file.

Global tasks on the other hand should be defined in the `Quickie` module in the user's directory.

Tasks are defined as classes, though factory functions are also supported.

### Why define tasks in Python?

While many existing similar tools use YAML, TOML or custom formats to define tasks, `quickie` uses Python for the following reasons:

- Built-in syntax highlighting and linting
- Supported by most editors and IDEs
- Easy to use and understand
- Extensible and powerful

### Quick Example

Here is a simple example of a `__quickie.py` file:

```python
from quickie import arg, script, task

@task(name=["hello", "greet"])
@arg("name", help="The name to greet")
def hello(name):
    """Greet someone"""  # added as the task help
    print(f"Hello, {name}!")


@script(extra_args=True)
def echo():
    return " ".join(["echo", *args])
```

You can run the `hello` task with the following command:

```sh
$ qck hello world
Hello, world!
$ qck greet world
Hello, world!
```

And the `script` task with:

```sh
$ qck echo Hello there
Hello there
```
