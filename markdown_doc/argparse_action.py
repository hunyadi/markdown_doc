"""
Generate Markdown documentation from Python code

Copyright 2024, Levente Hunyadi

:see: https://github.com/hunyadi/markdown_doc
"""

import argparse
import enum
from typing import Any, Iterable, Sequence, TypeVar

T = TypeVar("T")


class EnumValue:
    "Formats an enumeration value as its string representation."

    enum_value: enum.Enum

    def __init__(self, enum_value: enum.Enum) -> None:
        self.enum_value = enum_value

    def __repr__(self) -> str:
        return str(self.enum_value.value)

    def __str__(self) -> str:
        return str(self.enum_value.value)

    def __eq__(self, operand: object) -> bool:
        if not isinstance(operand, EnumValue):
            return False
        return operand.enum_value is self.enum_value


class EnumConverter:
    "Instantiates an enumeration value based on a case-insensitive string match."

    action: argparse.Action
    enum_type: type[enum.Enum]
    enum_values: dict[str, EnumValue]

    def __init__(self, action: argparse.Action, enum_type: type[enum.Enum]) -> None:
        self.action = action
        self.enum_type = enum_type
        self.enum_values = {}
        for member in enum_type:
            if not isinstance(member.value, str):
                raise TypeError(f"all members in enumeration `{enum_type.__name__}` must have a string value")
            enum_value = str(member.value).lower()
            if enum_value in self.enum_values:
                raise KeyError(f"enumeration `{enum_type.__name__}` has a duplicate value {repr(enum_value)} with a case-insensitive match")
            self.enum_values[enum_value] = EnumValue(member)

    def __call__(self, value: str) -> EnumValue:
        enum_value = self.enum_values.get(value.lower())
        if enum_value is None:
            args = ", ".join(f"'{e.value}'" for e in self.enum_type)
            raise argparse.ArgumentError(self.action, f"expected one of {args}")
        return enum_value


class _EnumAction(argparse.Action):
    """
    Accepts enumeration values with a case-insensitive match.

    This class is instantiated indirectly via `EnumAction`.
    """

    def __init__(
        self,
        enum_type: type[enum.Enum],
        option_strings: Sequence[str],
        dest: str,
        nargs: int | str | None = None,
        const: T | None = None,
        default: T | None = None,
        type: type[T] | None = None,
        choices: Iterable[T] | None = None,
        required: bool = False,
        help: str | None = None,
        metavar: str | tuple[str, ...] | None = None,
    ):
        """
        Invoked by :cls:`argparse.ArgumentParser` to create an :cls:`argparse.Action`.
        """

        if const is not None and not isinstance(const, enum.Enum):
            raise TypeError("expected: instance of type `enum.Enum` for argument `const`")
        if default is not None and not isinstance(default, enum.Enum):
            raise TypeError("expected: instance of type `enum.Enum` for argument `default`")
        if type is not None:
            raise TypeError("expected: `None` for argument `type` (inferred automatically)")
        if choices is not None:
            raise TypeError("expected: `None` for argument `choices` (inferred automatically)")

        super().__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=nargs,
            const=const,
            default=default,
            type=EnumConverter(self, enum_type),
            choices=[EnumValue(e) for e in enum_type],
            required=required,
            help=help,
            metavar=metavar,
        )

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ) -> None:
        """
        Invoked by :cls:`argparse.ArgumentParser` to apply the action to a command-line argument.
        """

        if isinstance(values, Sequence):
            for value in values:
                if not isinstance(value, EnumValue):
                    raise TypeError(f"expected: instance of `{EnumValue.__name__}`; got: `{type(value).__name__}`")
                setattr(namespace, self.dest, value.enum_value)
        else:
            if not isinstance(values, EnumValue):
                raise TypeError(f"expected: instance of `{EnumValue.__name__}`; got: `{type(values).__name__}`")
            setattr(namespace, self.dest, values.enum_value)


class EnumAction:
    """
    Accepts enumeration values with a case-insensitive match.
    """

    enum_type: type[enum.Enum]

    def __init__(self, enum_type: type[enum.Enum]):
        """
        Creates an object to be passed to `argparse.ArgumentParser.add_argument`.

        :param enum_type: The enumeration type to create the action for.
        """

        if not issubclass(enum_type, enum.Enum):
            raise TypeError("expected: enumeration type")

        self.enum_type = enum_type

    def __call__(
        self,
        option_strings: list[str],
        dest: str,
        nargs: int | str | None = None,
        const: Any | None = None,
        default: Any | None = None,
        type: type[Any] | None = None,
        choices: list[str] | None = None,
        required: bool = False,
        help: str | None = None,
        metavar: str | None = None,
    ) -> _EnumAction:
        return _EnumAction(
            self.enum_type,
            option_strings,
            dest,
            nargs,
            const,
            default,
            type,
            choices,
            required,
            help,
            metavar,
        )
