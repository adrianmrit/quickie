qk-mcp — MCP stdio server
=================================

Overview
--------

`qk-mcp` starts a FastMCP stdio server that exposes tasks defined in your
project's `_qk` module. This allows external clients to discover and execute tasks remotely via the MCP protocol. The server applies configuration options for task loading and logging before starting.

Usage
-----

.. code-block:: console

    qk-mcp [options]

Supported options
-----------------

- ``-m``, ``--module`` — Path to the tasks module or directory. When set,
  the server will load tasks from this path instead of discovering the
  project automatically.
- ``-g``, ``--global`` — Use global tasks from ``~/_qkg`` instead of project
  tasks.
- ``-v``, ``--verbose`` / ``-q``, ``--quiet`` — Increase / decrease
  verbosity for logging.
- ``--log-file`` — Path to a file where server logs should be written.

API
---

The MCP server exposes two tools via the FastMCP protocol:

- ``list_tasks`` — Returns metadata for available tasks (names, aliases,
  usage, help, and source location).
- ``run_task`` — Execute a named task in an isolated subprocess; accepts
  `args`, optional `stdin`, and a `timeout`. Output is streamed as MCP
  messages and the final captured result is returned.
