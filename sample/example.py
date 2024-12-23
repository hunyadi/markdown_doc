"""
This is a module with sample Python classes, exceptions, functions, etc.
"""

import enum
import sys
import typing
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Union

from strong_typing.auxiliary import int8, int16, uint32, uint64
from strong_typing.core import JsonType, Schema

SimpleType = bool | int | float | str


@enum.unique
class EnumType(enum.Enum):
    """
    This is an enumeration with unique values.
    """

    enabled = "enabled"
    "Documents the enumeration member `enabled`."

    disabled = "disabled"
    "Documents the enumeration member `disabled`."

    active = "active"
    inactive = "inactive"


class MyException(Exception):
    """
    A custom exception type.
    """


class PlainClass:
    """
    A plain class.

    :param timestamp: A member variable of type `datetime`.
    """

    timestamp: datetime


@dataclass
class SampleClass:
    """
    A data-class with several member variables.

    This class is extended by :class:`DerivedClass`.

    This class implements total ordering with :meth:`__lt__`, :meth:`SampleClass.__le__`, :meth:`SampleClass.__ge__` and :meth:`__gt__`.

    Class doc-strings can include code blocks.

    A code block formatted as HTML:

    ```html
    <html>
        <body>
            <p>A paragraph.</p>
        </body>
    </html>
    ```

    A code block formatted as Python:

    ```python
    if sys.version_info > (3, 10):
        SimpleType = bool | int | float | str
    ```

    See also: https://www.iana.org/help/example-domains

    :param boolean: A member variable of type `bool`.
    :param integer: A member variable of type `int`.
    :param double: A member variable of type `float`.
    :param string: A member variable of type `str`.
    :param enumeration: A member variable with an enumeration type.
    """

    boolean: bool
    integer: int
    double: float
    string: str
    enumeration: EnumType

    def __lt__(self, other: "SampleClass") -> bool:
        """
        A custom implementation for *less than*.

        :param other: A reference to :class:`SampleClass`.
        """

        return self.integer < other.integer

    def __le__(self, other: "SampleClass") -> bool:
        "A custom implementation for *less than or equal*."

        return self.integer <= other.integer

    def __ge__(self, other: "SampleClass") -> bool:
        "A custom implementation for *greater than or equal*."

        return self.integer >= other.integer

    def __gt__(self, other: "SampleClass") -> bool:
        "A custom implementation for *greater than*."

        return self.integer > other.integer

    def to_json(self) -> "JsonType":
        """
        Serializes the data to JSON.

        :returns: A JSON object.
        """

        return {
            "boolean": self.boolean,
            "integer": self.integer,
            "double": self.double,
            "string": self.string,
            "enumeration": self.enumeration.value,
        }

    @staticmethod
    def from_json(obj: "JsonType") -> "SampleClass":
        """
        De-serializes the data from JSON.

        :param obj: A JSON object.
        :returns: An instance of this class.
        """

        o = typing.cast(dict[str, JsonType], obj)
        return SampleClass(
            boolean=typing.cast(bool, o["boolean"]),
            integer=typing.cast(int, o["integer"]),
            double=typing.cast(float, o["double"]),
            string=typing.cast(str, o["string"]),
            enumeration=EnumType(o["enumeration"]),
        )


@dataclass
class DerivedClass(SampleClass):
    """
    This data-class derives from another base class.

    :param union: A union of several types.
    :param json: A complex type with type substitution.
    :param schema: A complex type without type substitution.
    """

    union: SimpleType
    json: JsonType
    schema: Schema


@dataclass
class FixedWidthIntegers:
    """
    Fixed-width integers have a compact representation.

    :param integer8: A signed integer of 8 bits.
    :param integer16: A signed integer of 16 bits.
    :param unsigned32: An unsigned integer of 32 bits.
    :param unsigned64: An unsigned integer of 64 bits.
    """

    integer8: int8
    integer16: int16
    unsigned32: uint32
    unsigned64: uint64


@dataclass
class OptionalValues:
    """
    A data-class with optional member variables.

    :param boolean: An optional member variable of type `bool`.
    :param integer: An optional member variable of type `int`.
    :param double: An optional member variable of type `float`.
    :param string: An optional member variable of type `str`.
    :param enumeration: An optional member variable with an enumeration type.
    :param complex: An optional member variable of a user-defined class.
    :param optional: A member variable with `typing.Optional`.
    :param union: A member variable with `typing.Union`.
    """

    boolean: bool | None
    integer: int | None
    double: float | None
    string: str | None
    enumeration: EnumType | None
    complex: SampleClass | None
    optional: Optional["SampleClass"]
    union: Union[SampleClass, "DerivedClass", None]


@dataclass
class LookupTable:
    """
    This table maps an integer key to a string value.

    :param id: Primary key.
    :param value: Lookup value.
    """

    id: int
    value: str


@dataclass
class EntityTable:
    """
    This class represents a table in a database or data warehouse.

    :param primary_key: Primary key of the table.
    :param updated_at: The time the record was created or last modified.
    :param foreign_key: A column with a foreign key to another table.
    :param unique_key: A column with unique values only.
    """

    primary_key: int
    updated_at: datetime
    foreign_key: LookupTable
    unique_key: str


def send_message(
    sender: str,
    recipient: str,
    message_body: str,
    priority: int = 1,
) -> int:
    """
    Sends a message.

    This function is in the same module as :class:`SampleClass` and :class:`DerivedClass`.

    :param sender: The person sending the message.
    :param recipient: The recipient of the message.
    :param message_body: The body of the message.
    :param priority: The priority of the message, can be a number 1-5.
    :returns: The message identifier.
    """
    return 23


if __name__ == "__main__":
    from pathlib import Path

    from markdown_doc.generator import MarkdownAnchorStyle, MarkdownGenerator, MarkdownOptions

    MarkdownGenerator([sys.modules[__name__]], options=MarkdownOptions(anchor_style=MarkdownAnchorStyle.GITBOOK)).generate(
        Path(__file__).parent.parent / "output"
    )
