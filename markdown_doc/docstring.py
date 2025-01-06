"""
Generate Markdown documentation from Python code

Copyright 2024-2025, Levente Hunyadi

:see: https://github.com/hunyadi/markdown_doc
"""

import ast
import inspect
from enum import Enum


def _try_get_assignment(stmt: ast.stmt) -> str | None:
    "Extracts the enumeration name for a member found in a class definition."

    if not isinstance(stmt, ast.Assign):
        return None
    if len(stmt.targets) != 1:
        return None
    target = stmt.targets[0]
    if not isinstance(target, ast.Name):
        return None
    return target.id


def _try_get_literal(stmt: ast.stmt) -> str | None:
    "Extracts the follow-up description for an enumeration member."

    if not isinstance(stmt, ast.Expr):
        return None
    if not isinstance(constant := stmt.value, ast.Constant):
        return None
    if not isinstance(docstring := constant.value, str):
        return None
    return docstring


def enum_labels(cls: type[Enum]) -> dict[str, str]:
    """
    Maps enumeration member names to their follow-up description.

    Python's own doc-string mechanism doesn't allow attaching a description to enumeration members. However,
    documentation toolchains such as Sphinx's `autodoc` support this with a string literal immediately following
    the enumeration member value assignment:

    ```
    @enum.unique
    class EnumType(enum.Enum):
        enabled = "enabled"
        "Documents the enumeration member `enabled`."

        disabled = "disabled"
        "Documents the enumeration member `disabled`."
    ```

    This function parses source code with Python's `ast` module to extract these description text strings.

    :param cls: An enumeration class type.
    :returns: Maps enumeration names to their description (if present).
    """

    body = ast.parse(inspect.getsource(cls)).body
    if len(body) != 1:
        raise TypeError("expected: a module with a single enumeration class")

    classdef = body[0]
    if not isinstance(classdef, ast.ClassDef):
        raise TypeError("expected: an enumeration class definition")

    enum_doc: dict[str, str] = {}
    enum_name: str | None = None
    for stmt in classdef.body:
        if enum_name is not None:
            # description must immediately follow enumeration member definition
            enum_desc = _try_get_literal(stmt)
            if enum_desc is not None:
                enum_doc[enum_name] = enum_desc
                enum_name = None
                continue

        enum_name = _try_get_assignment(stmt)
    return enum_doc
