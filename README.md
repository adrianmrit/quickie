# Quickie - A CLI tool for quick tasks

[![License](https://img.shields.io/github/license/adrianmrit/quickie)](https://github.com/adrianmrit/quickie/blob/master/LICENSE)

## Getting Started

### Prerequisites

Some prerequisites need to be installed.

- Python 3.12+

### Installing

Quickie can be installed via `pip` or `pipx`. This will add the `qck` binary and add the `quickie` package to your Python environment.

For example, if you want to run quickie for a single project, you can install it with `pip` under a virtual environment:

```sh
pip install quickie-runner
```

If you want to install `quickie` globally, you can either use `pip`, or `pipx` to install it in an isolated environment.

```sh
pipx install quickie-runner
```

See the [pipx installation instructions](https://pipx.pypa.io/stable/installation/)

You can use both installation methods, i.e. to use a version specific to a project, while running global
commands with the global installation.

## Tab completion

Tab completion is available for bash and zsh. It depends on the `argcomplete` package, which should have been installed with `quickie`.

To enable tab completion for `quickie`, add the following line to your `.bashrc` or `.zshrc`:

```sh
eval "$(register-python-argcomplete qck)"
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

Tasks are configured under a `__quickie.py` or `__quickie` python module in the current directory.
If using a `__quickie` directory, the tasks are defined in the `__quickie/__init__.py` file.

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


@script(extra_args=True, help="Echo the given arguments")
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
