qk-mcp — MCP stdio server
=================================

Overview
--------

``qk-mcp`` starts a FastMCP stdio server that exposes tasks defined in your
project's ``_qk`` module. This allows external clients (AI agents, IDE plugins,
etc.) to discover and execute tasks remotely via the MCP protocol.

A single ``qk-mcp`` process can serve **multiple projects** simultaneously.
Projects are declared at startup via ``--project`` or ``--config`` and remain
fixed for the lifetime of the server.

Usage
-----

.. code-block:: console

    qk-mcp [options]

Supported options
-----------------

- ``--project NAME:PATH`` — Register a project named *NAME* whose ``_qk``
  module or directory is at *PATH*. Repeatable; later declarations with the
  same name override earlier ones.
- ``--config FILE`` — Path to a TOML or JSON file that declares projects:

  .. code-block:: toml

      [projects]
      myapp = "/home/user/projects/myapp/_qk"
      infra  = "/home/user/infra/_qk"

  ``--project`` flags override config entries with the same name.
- ``-v``, ``--verbose`` / ``-q``, ``--quiet`` — Increase / decrease
  verbosity for logging.
- ``--log-file PATH`` — Path to a file where server logs should be written.

Project registration order
--------------------------

1. **Config file** (``--config``) — lowest priority.
2. **``--project`` flags** — override config on name conflict.
3. **CWD fallback** — when neither ``--config`` nor ``--project`` is given,
   the server discovers the project from the current working directory,
   using the directory name as the project alias.

API
---

The MCP server exposes two tools via the FastMCP protocol:

``list_tasks``
~~~~~~~~~~~~~~

Returns task metadata grouped by project.

Parameters:

- ``project`` *(optional)* — Alias or path of a registered project.
  When supplied, only that project's tasks are returned.
  When omitted, tasks for **all** registered projects are returned.

Each entry in the returned list contains:

- ``project`` — the project alias registered at startup.
- ``project_root`` — absolute path to the project root directory, or
  ``null`` if the root could not be determined.
- ``tasks`` — list of task metadata dicts, each with:

  - ``name`` — canonical task name.
  - ``aliases`` — all invocation aliases.
  - ``short_help``, ``help`` — description strings.
  - ``usage`` — CLI usage line.
  - ``location`` — source file and line.
  - ``args_schema`` — list of argument descriptors (``flags``, ``dest``,
    ``type``, ``default``, ``required``, ``choices``, ``help``, ``nargs``).

``run_task``
~~~~~~~~~~~~

Executes a named task in an isolated subprocess.

Parameters:

- ``task_name`` — name or alias of the task to run.
- ``args`` *(optional)* — command-line arguments to pass to the task.
- ``stdin`` *(optional)* — string written to the subprocess stdin (for
  interactive prompts). When omitted, stdin is closed immediately (DEVNULL).
- ``timeout`` *(optional, default 60)* — maximum wall-clock seconds. The
  subprocess is killed and a ToolError raised if exceeded.
- ``project`` *(optional)* — alias or path of a registered project. Required
  when multiple projects are configured; may be omitted when only one project
  is registered.

Returns ``{"exit_code": int, "stdout": str, "stderr": str}``. Stdout is
also streamed to the client as MCP info messages in real time.

Multi-project example
---------------------

Start the server with two projects:

.. code-block:: console

    qk-mcp --project myapp:/home/user/myapp/_qk --project infra:/home/user/infra/_qk

Or with a config file:

.. code-block:: console

    qk-mcp --config /home/user/.config/qk-mcp.toml

Then from a client:

.. code-block:: javascript

    // Step 1 — discover tasks in all projects
    list_tasks({})
    // → [{"project": "myapp", "project_root": "...", "tasks": [...]},
    //    {"project": "infra",  "project_root": "...", "tasks": [...]}]

    // Step 2 — run a task in myapp
    run_task({"task_name": "build", "project": "myapp"})

    // Step 3 — list tasks in infra only
    list_tasks({"project": "infra"})
