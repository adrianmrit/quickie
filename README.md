# Quickie - A CLI tool for quick tasks

[![License](https://img.shields.io/github/license/adrianmrit/quickie)](https://github.com/adrianmrit/quickie/blob/master/LICENSE)

## Getting Started

### Prerequisites

Some prerequisites need to be installed.

- Python 3.12+

### Installing

The recommended way to install `quickie` is via `pipx`.

With `pipx` you can add the `qck` command and the package in an isolated environment, without polluting your global Python environment.

See the [pipx installation instructions](https://pipx.pypa.io/stable/installation/)

After installing `pipx`, you can install `quickie` with the following command:

```sh
pipx install quickie-runner
```

You can also install `quickie` with `pip`:

```sh
pip install quickie-runner
```

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
from quickie.tasks import Task, ScriptTask

class hello(Task):
    def run(self):
        print("Hello, world!")


class ScriptTaskExample(ScriptTask):
    class Meta:
        alias = "echo"
        allow_unknown_args = True

    def get_script(self, *args):
        return " ".join(["echo", *args])
```

You can run the `Hello` task with the following command:

```sh
qck hello
```

And the `ScriptTaskExample` task with:

```sh
qck echo "Hello, world!"
```
