"""
Generate Markdown documentation from Python code

Copyright 2024-2026, Levente Hunyadi

:see: https://github.com/hunyadi/markdown_doc
"""

import sys
import typing
from collections.abc import Callable
from dataclasses import dataclass
from types import ModuleType, UnionType
from typing import Any, ForwardRef, Literal, ParamSpec, TypeVar, Union

if sys.version_info >= (3, 11):
    from typing import LiteralString as LiteralString
    from typing import Self as Self
else:
    from typing_extensions import LiteralString as LiteralString
    from typing_extensions import Self as Self


def is_union_type(tp: Any) -> bool:
    """
    `True` if `tp` is a union type such as `A | B` or `Union[A, B]`.
    """

    origin = typing.get_origin(tp)
    return origin is Union or origin is UnionType


def is_optional_type(tp: Any) -> bool:
    """
    `True` if `tp` is an optional type such as `T | None`, `Optional[T]` or `Union[T, None]`.
    """

    return is_union_type(tp) and any(a is type(None) for a in typing.get_args(tp))


def evaluate_type(typ: Any, module: ModuleType) -> Any:
    """
    Evaluates a forward reference type.

    :param typ: The type to convert, typically a dataclass member type.
    :param module: The context for the type, i.e. the module in which the member is defined.
    :returns: The evaluated type.
    """

    if isinstance(typ, str):
        # evaluate data-class field whose type annotation is a string
        return eval(typ, module.__dict__, locals())
    if isinstance(typ, ForwardRef):
        if sys.version_info >= (3, 14):
            return typing.evaluate_forward_ref(typ, owner=module)
        elif sys.version_info >= (3, 13):
            return typ._evaluate(
                module.__dict__,
                locals(),
                type_params=(),
                recursive_guard=frozenset(),
            )
        else:
            return typ._evaluate(
                module.__dict__,
                locals(),
                recursive_guard=frozenset(),
            )
    else:
        return typ


@dataclass(kw_only=True)
class TypeFormatterOptions:
    """
    Options for type formatter.

    Type and value transforms allow us to customize the string emitted for a specific type or literal value.

    Auxiliary types help give compact names to extended types. For example, consider the following type definitions:

    ```
    JsonType = None | bool | int | float | str | dict[str, "JsonType"] | list["JsonType"]
    int16 = Annotated[int, Signed(True), Storage(2), IntegerRange(-32768, 32767)]
    ```

    Here, we want the documentation generator to emit `JsonType` and `int16` for these types rather than their lengthy definition.

    :param type_transform: Transformation to apply to types before a string is emitted, e.g. to create a link in a documentation.
    :param value_transform: Transformation to apply to values (e.g. in arguments to `Literal`) before a string is emitted.
    :param auxiliary_types: Maps each Python type (typically `Annotated[T, ...]`) to a human-readable name.
    """

    type_transform: Callable[[type], str] | None
    value_transform: Callable[[Any], str] | None
    auxiliary_types: dict[object, str]


class TypeFormatter:
    """
    Converts a simple, composite or generic type to a string representation.
    """

    context: ModuleType | None
    options: TypeFormatterOptions

    def __init__(
        self,
        *,
        context: ModuleType | None = None,
        options: TypeFormatterOptions | None = None,
    ) -> None:
        """
        Initializes a type formatter.

        :param context: The module in the context of which forward references are evaluated.
        :param options: Options that control how documentation is generated.
        """

        self.context = context
        self.options = options if options is not None else TypeFormatterOptions(type_transform=None, value_transform=None, auxiliary_types={})

    def value_to_str(self, value: Any) -> str:
        """
        Emits a string for a value, such as those in arguments to the special form `Literal`.

        :param value: Value (of any type) for which to generate a string representation.
        """

        if self.options.value_transform is not None:
            return self.options.value_transform(value)
        else:
            return repr(value)

    def union_to_str(self, data_type_args: tuple[Any, ...]) -> str:
        """
        Emits a union of types as a string.

        :param data_type_args: A tuple of `(X,Y,Z)` for a union of `X | Y | Z` or `Union[X, Y, Z]`.
        """

        return " | ".join(self.python_type_to_str(t) for t in data_type_args)

    def plain_type_to_str(self, data_type: Any) -> str:
        "Returns the string representation of a Python type without metadata."

        if data_type is Self:
            return "Self"
        elif data_type is LiteralString:
            return "LiteralString"
        elif isinstance(data_type, ForwardRef):
            # return forward references as the annotation string

            fwd: ForwardRef = data_type
            fwd_arg = fwd.__forward_arg__

            if self.context is None:
                return fwd_arg

            context_type = getattr(self.context, fwd_arg, None)
            if context_type is None:
                return self.python_type_to_str(evaluate_type(fwd_arg, self.context))

            if isinstance(context_type, type) and self.options.type_transform is not None:
                return self.options.type_transform(context_type)

            return fwd_arg
        elif isinstance(data_type, str):
            if self.context is None:
                if data_type.isidentifier():
                    # don't evaluate expressions that are simple identifiers
                    return data_type

                raise ValueError("missing context for evaluating types")

            if data_type.isidentifier() and data_type in self.context.__dict__:
                # simple type name that is defined in the current context
                return data_type

            return self.python_type_to_str(evaluate_type(data_type, self.context))
        elif isinstance(data_type, ParamSpec):
            return data_type.__name__
        elif isinstance(data_type, TypeVar):
            return data_type.__name__

        origin = typing.get_origin(data_type)
        if origin is not None:
            data_type_args = typing.get_args(data_type)

            if origin is dict:  # dict[K, V]
                origin_name = "dict"
            elif origin is list:  # list[T]
                origin_name = "list"
            elif origin is set:  # set[T]
                origin_name = "set"
            elif origin is frozenset:  # frozenset[T]
                origin_name = "frozenset"
            elif origin is tuple:  # tuple[T, ...]
                origin_name = "tuple"
            elif origin is type:  # type[T]
                args = ", ".join(self.python_type_to_str(t) for t in data_type_args)
                return f"type[{args}]"
            elif origin is Literal:
                args = ", ".join(self.value_to_str(arg) for arg in data_type_args)
                return f"Literal[{args}]"
            elif is_optional_type(data_type) or is_union_type(data_type):
                return self.union_to_str(data_type_args)
            else:
                origin_name = origin.__name__

            args = ", ".join(self.python_type_to_str(t) for t in data_type_args)
            return f"{origin_name}[{args}]"

        if not isinstance(data_type, type):
            raise ValueError(f"not a type, generic type, or type-like object: {data_type} (of type {type(data_type)})")

        if self.options.type_transform is not None:
            return self.options.type_transform(data_type)
        else:
            return data_type.__name__

    def python_type_to_str(self, data_type: Any) -> str:
        "Returns the string representation of a Python type."

        if data_type is None or data_type is type(None):
            return "None"
        elif data_type is Ellipsis or data_type is type(Ellipsis):
            return "..."
        elif data_type is Any:
            return "Any"
        elif isinstance(data_type, list):  # e.g. in `Callable[[bool, int], str]`
            callable_args = typing.cast(list[Any], data_type)  # type: ignore[redundant-cast]
            items = ", ".join(self.python_type_to_str(item) for item in callable_args)
            return f"[{items}]"

        # use compact name for alias types
        name = self.options.auxiliary_types.get(data_type)
        if name is not None:
            return name

        meta_data = getattr(data_type, "__metadata__", None)
        if meta_data is not None:
            # type is Annotated[T, ...]
            meta_tuple: tuple[Any, ...] = meta_data
            arg = typing.get_args(data_type)[0]

            # check for auxiliary types with user-defined annotations
            meta_set = set(meta_tuple)
            for auxiliary_type, auxiliary_name in self.options.auxiliary_types.items():
                auxiliary_arg = typing.get_args(auxiliary_type)[0]
                if arg is not auxiliary_arg:
                    continue

                auxiliary_meta_tuple: tuple[Any, ...] | None = getattr(auxiliary_type, "__metadata__", None)
                if auxiliary_meta_tuple is None:
                    continue

                if meta_set.issuperset(auxiliary_meta_tuple):
                    # type is an auxiliary type with extra annotations
                    auxiliary_args = ", ".join(repr(m) for m in meta_tuple if m not in auxiliary_meta_tuple)
                    return f"Annotated[{auxiliary_name}, {auxiliary_args}]"

            # type is an annotated type
            args = ", ".join(repr(m) for m in meta_tuple)
            return f"Annotated[{self.plain_type_to_str(arg)}, {args}]"
        else:
            # type is a regular type
            return self.plain_type_to_str(data_type)
