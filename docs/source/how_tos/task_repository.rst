Task Repository
==========================

When working with multiple projects it is common to have common tasks between them. One way to have these tasks
in a single place is to have a separate repository. These tasks can then be imported into the projects
that need them. Python does not usually allow importing from a folder outside the current module, but Quickie provides
:func:`quickie.utils.imports.import_from_path`, which allows you to retrieve a module from a path.

For example, it could work like this:
.. code-block:: python

    from quickie import task, Namespace
    from quickie.utils.imports import import_from_path

    # Import the module from the path
    # ENV variables or other methods could be used to set the path, since
    # different users could have the projects in different locations
    my_module = import_from_path("/path/to/my/module.py")

    namespace = Namespace(
        {
            # Insert tasks from the common module into the root namespace
            "": my_module.namespace,
        }
    )

    # Use the imported module
    @task
    def my_task():
        my_module.my_function()


This idea can also be used to keep a backup of private tasks in a separate repository, i.e. a private GitHub repository.
For example, the project could have a setup like this:
.. code-block:: python

    # main_project/_qk/__init__.py

    ...

    namespace = Namespace()

    try:
        # Assuming it is git ignored but can be defined by the user
        from . import private
        namespace.add(private)
    except ImportError:
        pass

    # main_project/_qk/private.py
    from quickie.utils.imports import import_from_path
    from quickie import Namespace

    namespace = Namespace(
        {
            # Tasks defined in your private project
            "": import_from_path("/private_repo/tasks.py").namespace,
        }
    )

The same idea could be used to use Quickie in a project that is not using it, for example
add ``_qk`` or ``_qk.py`` to ``.gitignore`` or ``.git/info/exclude`` and either define your
tasks there or load them from a private project as shown above.

Packages with tasks could also be installed as dependencies.
Then could simply import the package instead of using :func:`quickie.utils.imports.import_from_path`.
