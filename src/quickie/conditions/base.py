"""Contains the base classes for task conditions.

Conditions are used to determine if a task should be executed or not.
They can be combined using & (and), | (or), ^ (xor), and ~ (not) to create
more complex conditions.
"""

import abc
import typing

if typing.TYPE_CHECKING:
    from quickie.tasks import Task as TaskInstance
else:
    type TaskInstance = typing.Any


class BaseCondition(abc.ABC):
    """Base class for all conditions."""

    @abc.abstractmethod
    def __call__(self, task: TaskInstance, *args, **kwargs):
        """Check if the condition is met.

        :param task: The task to check.
        :param args: Task arguments.
        :param kwargs: Task keyword arguments.

        :returns: True if the condition is met, False otherwise.
        """

    def __and__(self, other: "BaseCondition"):
        """Combine two conditions with and."""
        return _AndCondition(self, other)

    def __or__(self, other: "BaseCondition"):
        """Combine two conditions with or."""
        return _OrCondition(self, other)

    def __xor__(self, other: "BaseCondition"):
        """Combine two conditions with xor."""
        return _XorCondition(self, other)

    def __invert__(self):
        """Invert the condition."""
        return _NotCondition(self)

    @typing.override
    def __repr__(self):
        return self.__class__.__name__ + "()"


# ! We don't use operator to simplify the code as
# ! we want to avoid evaluating a second condition
# ! if the first one is False


class _AndCondition(BaseCondition):
    def __init__(self, condition1, condition2):
        self.condition1 = condition1
        self.condition2 = condition2

    @typing.override
    def __call__(self, task, *args, **kwargs):
        return self.condition1(task, *args, **kwargs) and self.condition2(
            task, *args, **kwargs
        )

    def __repr__(self):
        return f"{self.condition1!r} & {self.condition2!r}"


class _OrCondition(BaseCondition):
    def __init__(self, condition1, condition2):
        self.condition1 = condition1
        self.condition2 = condition2

    @typing.override
    def __call__(self, task, *args, **kwargs):
        return self.condition1(task, *args, **kwargs) or self.condition2(
            task, *args, **kwargs
        )

    def __repr__(self):
        return f"{self.condition1!r} | {self.condition2!r}"


class _XorCondition(BaseCondition):
    def __init__(self, condition1, condition2):
        self.condition1 = condition1
        self.condition2 = condition2

    @typing.override
    def __call__(self, task, *args, **kwargs):
        return bool(self.condition1(task, *args, **kwargs)) ^ bool(
            self.condition2(task, *args, **kwargs)
        )

    def __repr__(self):
        return f"{self.condition1!r} ^ {self.condition2!r}"


class _NotCondition(BaseCondition):
    def __init__(self, condition):
        self.condition = condition

    @typing.override
    def __call__(self, task, *args, **kwargs):
        return not self.condition(task, *args, **kwargs)

    def __repr__(self):
        return f"~{self.condition!r}"
