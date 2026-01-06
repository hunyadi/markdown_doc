"""
Generate Markdown documentation from Python code

Copyright 2024-2026, Levente Hunyadi

:see: https://github.com/hunyadi/markdown_doc
"""

import sys
from dataclasses import dataclass
from typing import Annotated, TypeAlias


@dataclass(eq=True, frozen=True)
class Alias:
    """
    Alternative name of a property, typically used in JSON serialization.

    :param name: The secondary name.
    """

    name: str


@dataclass(eq=True, frozen=True)
class Signed:
    """
    Signed-ness of an integer type.

    :param is_signed: True if the integer type is a signed type.
    """

    is_signed: bool


@dataclass(eq=True, frozen=True)
class Storage:
    """
    Number of bytes the binary representation of an integer type takes, e.g. 4 bytes for an int32.

    :param bytes: Number of types to store the fixed-width integer type.
    """

    bytes: int


@dataclass(eq=True, frozen=True)
class IntegerRange:
    """
    Minimum and maximum value of an integer. The range is inclusive.

    :param minimum: The minimum value the fixed-width integer type can take.
    :param maximum: The maximum value the fixed-width integer type can take.
    """

    minimum: int
    maximum: int


@dataclass(eq=True, frozen=True)
class Precision:
    """
    Precision of a floating-point value.

    :param significant_digits: Total number of significant decimal digits.
    :param decimal_digits: Number of decimal digits in the fractional part.
    """

    significant_digits: int
    decimal_digits: int = 0

    @property
    def integer_digits(self) -> int:
        "Number of decimal digits in the integer part."

        return self.significant_digits - self.decimal_digits


@dataclass(eq=True, frozen=True)
class TimePrecision:
    """
    Precision of a timestamp or time interval.

    :param decimal_digits: Number of fractional digits retained in the sub-seconds field for a timestamp.
    """

    decimal_digits: int = 0


@dataclass(eq=True, frozen=True)
class Length:
    """
    Exact length of a string.

    :param value: Number of characters.
    """

    value: int


@dataclass(eq=True, frozen=True)
class MinLength:
    """
    Minimum length of a string.

    :param value: Minimum number of characters.
    """

    value: int


@dataclass(eq=True, frozen=True)
class MaxLength:
    """
    Maximum length of a string.

    :param value: Maximum number of characters.
    """

    value: int


@dataclass(eq=True, frozen=True)
class SpecialConversion:
    "Indicates that the annotated type is subject to custom conversion rules."


int8: TypeAlias = Annotated[int, Signed(True), Storage(1), IntegerRange(-128, 127)]
int16: TypeAlias = Annotated[int, Signed(True), Storage(2), IntegerRange(-32768, 32767)]
int32: TypeAlias = Annotated[
    int,
    Signed(True),
    Storage(4),
    IntegerRange(-2147483648, 2147483647),
]
int64: TypeAlias = Annotated[
    int,
    Signed(True),
    Storage(8),
    IntegerRange(-9223372036854775808, 9223372036854775807),
]

uint8: TypeAlias = Annotated[int, Signed(False), Storage(1), IntegerRange(0, 255)]
uint16: TypeAlias = Annotated[int, Signed(False), Storage(2), IntegerRange(0, 65535)]
uint32: TypeAlias = Annotated[
    int,
    Signed(False),
    Storage(4),
    IntegerRange(0, 4294967295),
]
uint64: TypeAlias = Annotated[
    int,
    Signed(False),
    Storage(8),
    IntegerRange(0, 18446744073709551615),
]

float32: TypeAlias = Annotated[float, Storage(4)]
float64: TypeAlias = Annotated[float, Storage(8)]

# maps globals of type Annotated[T, ...] defined in this module to their string names
AUXILIARY_TYPES: dict[object, str] = {}
module = sys.modules[__name__]
for var in dir(module):
    typ = getattr(module, var)
    if getattr(typ, "__metadata__", None) is not None:
        # type is Annotated[T, ...]
        AUXILIARY_TYPES[typ] = var
