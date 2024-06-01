# task-mom - A CLI tool that does your chores while you slack off

[![Code style: yapf](https://img.shields.io/badge/code%20style-yapf-blue)](https://github.com/google/yapf)
[![License](https://img.shields.io/github/license/adrianmrit/task-mom)](https://github.com/adrianmrit/task-mom/blob/master/LICENSE)

## Getting Started

### Prerequisites

Some prerequisites need to be installed.

- Python 3.12+

### Installing

The recommended way to install `task-mom` is via `pipx`.

With `pipx` you can install `task-mom` in an isolated environment, without polluting your global Python environment.

See the [pipx installation instructions](https://pipx.pypa.io/stable/installation/)

After installing `pipx`, you can install `task-mom` with the following command:

```sh
pipx install task-mom
```

You can also install `task-mom` with `pip`:

```sh
pip install task-mom
```

## Tab completion

Tab completion is available for bash and zsh. It depends on the `argcomplete` package, which should have been installed with `task-mom`.

To enable tab completion for `task-mom`, add the following line to your `.bashrc` or `.zshrc`:

```sh
eval "$(register-python-argcomplete task-mom)"
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

To be done.
