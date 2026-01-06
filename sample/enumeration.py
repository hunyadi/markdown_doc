"""
Generate Markdown documentation from Python code

Copyright 2024-2026, Levente Hunyadi

:see: https://github.com/hunyadi/markdown_doc
"""

import sys
from collections.abc import Callable
from enum import Enum, unique
from typing import Any


def extend_enum(source: type[Enum]) -> Callable[[type[Enum]], type[Enum]]:
    """
    Creates a new enumeration type extending the set of values in an existing type.

    :param source: The existing enumeration type to be extended with new values.
    :returns: A new enumeration type with the extended set of values.
    """

    def wrap(extend: type[Enum]) -> type[Enum]:
        # create new enumeration type combining the values from both types
        values: dict[str, Any] = {}
        values.update((e.name, e.value) for e in source)
        values.update((e.name, e.value) for e in extend)
        enum_class: type[Enum] = Enum(extend.__name__, values)  # type: ignore

        # assign the newly created type to the same module where the extending class is defined
        enum_class.__module__ = extend.__module__
        enum_class.__doc__ = extend.__doc__
        setattr(sys.modules[extend.__module__], extend.__name__, enum_class)

        return unique(enum_class)

    return wrap
