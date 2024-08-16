# Quickie Global

This package provides a separate binary `qckg` that allows you to run global quickie tasks from any directory, without conflicts with quickie tasks defined in your projects.

## Installing

Do not install this package directly. Instead, install [quickie-runner](
    https://pypi.org/project/quickie-runner/
) with the `global` option. This will install both `quickie-runner` and `quickie-runner-global`.

It is recommended to use `pipx` to install in an isolated environment:

    ```sh
    pipx install quickie-runner[global]
    qck --help
    qckg --help
    ```
