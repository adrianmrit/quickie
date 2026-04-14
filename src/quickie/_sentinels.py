"""Shared sentinel values used to distinguish omitted parameters."""

import enum
import typing


class DefaultValue(enum.Enum):
    """Sentinel values representing framework defaults."""

    USE_DEFAULT = enum.auto()


USE_DEFAULT = DefaultValue.USE_DEFAULT
"""Sentinel value for "parameter omitted; use default policy"."""

type UseDefault = typing.Literal[DefaultValue.USE_DEFAULT]
"""Type alias for values that explicitly represent "use default"."""
