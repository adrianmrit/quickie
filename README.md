# Quickie - A CLI tool that does your chores while you slack off

[![Code style: yapf](https://img.shields.io/badge/code%20style-yapf-blue)](https://github.com/google/yapf)
[![License](https://img.shields.io/github/license/adrianmrit/quickie)](https://github.com/adrianmrit/quickie/blob/master/LICENSE)

## Getting Started

### Prerequisites

Some prerequisites need to be installed.

- Python 3.12+

### Installing

The recommended way to install `quickie` is via `pipx`.

With `pipx` you can install `quickie` in an isolated environment, without polluting your global Python environment.

See the [pipx installation instructions](https://pipx.pypa.io/stable/installation/)

After installing `pipx`, you can install `quickie` with the following command:

```sh
pipx install quickie
```

You can also install `quickie` with `pip`:

```sh
pip install quickie
```

## Tab completion

Tab completion is available for bash and zsh. It depends on the `argcomplete` package, which should have been installed with `quickie`.

To enable tab completion for `quickie`, add the following line to your `.bashrc` or `.zshrc`:

```sh
eval "$(register-python-argcomplete quickie)"
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
