Namespaces
==========

When having a large number of tasks, it's useful to organize them into logical groups.
The best way to do so is to create separate modules for each group of tasks and then import them at the root level.
While we could simple import all tasks from the modules, there is a chance of name conflicts and can create
confusion. To avoid this, we can use namespaces.

Namespaces are defined by creating an instance of the `Namespace` class and adding modules, other namespaces, or tasks to it.

.. WARNING::
    Tasks and namespaces are loaded in the order they are defined. When a namespace is found, it will be fully
    loaded (i.e. recursively) before moving on to the next task or namespace.

.. WARNING::
    Simply creating a `Namespace` instance will not load the tasks. The namespace is discovered at the time of
    loading tasks, by going through the attributes of the module. Therefore it is important to define the namespace
    as a global variable in the module, or nested within other namespaces.

For example:

.. code-block:: python

    # MyProject/_qk/__init__.py
    from quickie import Namespace
    from . import public, private, test
    try:
        from . import private
    except ImportError:
        private = None

    namespace = Namespace(
        {
            # Test and public tasks are available at the root.
            # If there are tasks with the same name, those under `public` will be used
            # as it is loaded last, overriding the `test` tasks with the same name.
            "": [test, public],
            # Original public tasks are still available under `public:`
            "public": public,
            # Original test tasks are still available under `test:`
            "test": test,
        }
    )
    if private is not None:
        # Adds the private tasks under the root namespace
        # Because it is added last, it will override any tasks with the same name
        # from the other modules.
        namespace.add(private)
        # Adds the private tasks under the `private` namespace
        namespace.add(private, "private")


It might also be useful to add the tasks directly to the namespace instance.

.. code-block:: python

    # MyProject/_qk/__init__.py
    from quickie import Namespace, task
    try:
        from . import private
    except ImportError:
        private = None

    namespace = Namespace()

    @task
    def hello(name):
        return f"echo 'Hello, {name}!'"

    @task
    def bye(name):
        return f"echo 'Bye, {name}!'"

    # Task will be available as `namespace:hello`
    namespace.add(hello, "namespace")
    # Multiple tasks can be added at once under the same namespace
    namespace.add([hello, bye], "namespace")

Namespaces can be nested, allowing for a hierarchical structure.

.. code-block:: python

    # MyProject/_qk/__init__.py
    from quickie import Namespace
    from . import module1, module2, module3

    namespace = Namespace(
        {
            "a": module1,
            # Mappings can be used
            "b": {
                "": module2,
                "1": module3,
            },
            "c": Namespace(
                {
                    "": module1,
                    "1": module2,
                }
            )
        }
    )

Multiple namespace instances can also be defined.

.. code-block:: python

    # MyProject/_qk/__init__.py
    from quickie import Namespace
    from . import module1, module2, module3

    # Under the root namespace
    namespace1 = Namespace()
    # Also under the root namespace
    namespace2 = Namespace()
    # Under the `a` namespace
    namespace3 = Namespace(path="a")
    ...
