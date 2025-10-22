"""
Generate Markdown documentation from Python code

Copyright 2024-2025, Levente Hunyadi

:see: https://github.com/hunyadi/markdown_doc
"""

import enum
import inspect
import logging
import os
import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import FunctionType, MethodType, ModuleType
from typing import Any, Callable, TypeGuard

from strong_typing.docstring import DocstringSeeAlso, check_docstring, parse_type
from strong_typing.inspection import DataclassInstance, TypeLike, get_module_classes, get_module_functions, is_dataclass_type, is_type_enum
from strong_typing.name import TypeFormatter

from .docstring import enum_labels
from .resolver import ClassResolver, MemberFunctionResolver, MemberResolver, ModuleFunctionResolver, ModuleResolver, Resolver


def replace_links(text: str) -> str:
    """
    Replaces plain text URLs with Markdown links.

    :param text: String with possible occurrences of URLs.
    :returns: String with replacements made.
    """

    regex = re.compile(
        r"""
        \b
        (                                  # Capture 1: entire matched URL
        (?:
            https?:                        # URL protocol and colon
            (?:
            /{1,3}                         # 1-3 slashes
            |                              #   or
            [a-z0-9%]                      # Single letter or digit or '%'
                                           # (Trying not to match e.g. "URI::Escape")
            )
            |                              #   or
                                           # looks like domain name followed by a slash:
            [a-z0-9.\-]+[.]
            (?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|
            ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|
            by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|
            eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|
            im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|
            md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|
            pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|sk|sl|sm|sn|so|sr|ss|st|
            su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|
            wf|ws|ye|yt|yu|za|zm|zw)
            /
        )
        [^\s()<>{}\[\]]*                   # 0+ non-space, non-()<>{}[]
        (?:                                # 0+ times:
            \(                             #   Balanced parens containing:
            [^\s()]*                       #   0+ non-paren chars
            (?:                            #   0+ times:
            \([^\s()]*\)                   #     Inner balanced parens containing 0+ non-paren chars
            [^\s()]*                       #     0+ non-paren chars
            )*
            \)
            [^\s()<>{}\[\]]*               # 0+ non-space, non-()<>{}[]
        )*
        (?:                                # End with:
            \(                             #   Balanced parens containing:
            [^\s()]*                       #   0+ non-paren chars
            (?:                            #   0+ times:
            \([^\s()]*\)                   #     Inner balanced parens containing 0+ non-paren chars
            [^\s()]*                       #     0+ non-paren chars
            )*
            \)
            |                              #   or
            [^\s`!()\[\]{};:'".,<>?«»“”‘’] # not a space or one of these punctuation chars
        )
        |					# OR, the following to match naked domains:
        (?:
            (?<!@)			# not preceded by a @, avoid matching foo@_gmail.com_
            [a-z0-9]+
            (?:[.\-][a-z0-9]+)*
            [.]
            (?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|
            ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|
            by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|
            eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|
            im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|
            md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|
            pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|sk|sl|sm|sn|so|sr|ss|st|
            su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|
            wf|ws|ye|yt|yu|za|zm|zw)
            \b
            /?
            (?!@)			# not succeeded by a @, avoid matching "foo.na" in "foo.na@example.com"
        )
        )
        """,
        re.VERBOSE | re.UNICODE,
    )
    text, count = regex.subn(r"[\1](\1)", text)
    logging.debug("%d URL(s) found", count)
    return text


def quote_value(value: Any) -> str:
    "Renders a value as Markdown preformatted text."

    s = repr(value)
    if "`" not in s:
        return f"`{s}`"
    elif "``" not in s:
        return f"``{s}``"
    else:
        return f"```{s}```"


def safe_name(name: str) -> str:
    "Object name with those characters escaped that are allowed in Python identifiers but have special meaning in Markdown."

    regex = re.compile(r"(\b_+|_+\b)")
    return regex.sub(lambda m: m.group(0).replace("_", "\\_"), name)


def _safe_id_part(part: str) -> str:
    if part.startswith("__"):
        return f"sp{part}"  # special member variable or function
    elif part.startswith("_"):
        return f"p{part}"  # private member variable or function
    else:
        return part


def safe_id(name: str) -> str:
    """
    Object identifier that qualifies as a Markdown anchor.

    The generated identifier is used as an anchor for Markdown links.

    Usually, the identifier matches the class or function name. However, objects with private visibility have a name
    that begins with `_`, and the name of special methods starts with `__`, both of which confuses many Markdown
    formatting engines. We take a safe approach to prefix these with `p` and `sp`, respectively.
    """

    parts = name.split(".")
    return ".".join(_safe_id_part(part) for part in parts)


def module_path(target: str, source: str) -> str:
    """
    Returns a relative path from source to target.

    :param target: The fully qualified name of the module to link to (in dot notation).
    :param source: The fully qualified name of the module to link from (in dot notation).
    """

    target_path = Path("/" + target.replace(".", "/") + ".md")
    source_path = Path("/" + source.replace(".", "/") + ".md")
    target_dir = target_path.parent
    source_dir = source_path.parent
    if sys.version_info >= (3, 12):
        relative_path = Path(target_dir).relative_to(source_dir, walk_up=True)
    else:
        relative_path = Path(os.path.relpath(target_dir, start=source_dir))
    return (relative_path / target_path.name).as_posix()


CallableType = Callable[..., Any]


def is_function(fn: Any) -> TypeGuard[CallableType]:
    "Identifies module-level functions, class member functions, functions with `@classmethod` and `@staticmethod`."

    return isinstance(fn, FunctionType) or isinstance(fn, MethodType) or isinstance(fn, classmethod) or isinstance(fn, staticmethod)


@enum.unique
class ObjectKind(enum.Enum):
    "Represents a group of Python types, e.g. regular classes, data-classes, enumerations, module-level functions, etc."

    CLASS = "class"
    "Group for regular classes."

    DATACLASS = "dataclass"
    "Group for data-classes."

    ENUM = "enum"
    "Group for enumerations."

    FUNCTION = "function"
    "Group for module-level functions."

    MODULE = "module"
    "Group for modules."


ObjectType = type | CallableType


def object_kind(cls: ObjectType | ModuleType) -> ObjectKind:
    "Determines the group of types that the passed type belongs to."

    if isinstance(cls, ModuleType):
        return ObjectKind.MODULE
    elif isinstance(cls, FunctionType):  # module-level function
        return ObjectKind.FUNCTION
    elif is_dataclass_type(cls):
        return ObjectKind.DATACLASS
    elif is_type_enum(cls):
        return ObjectKind.ENUM
    else:
        return ObjectKind.CLASS


@dataclass
class Context:
    """
    Represents a group of types that are exported as a unit.

    :param module: The module in which the types are defined.
    :param partition: Identifies the group of types.
    """

    module: ModuleType
    partition: ObjectKind | None

    def name(self) -> str:
        if self.partition is not None:
            return f"{self.module.__name__}-{self.partition.value}"
        else:
            return self.module.__name__

    def matches(self, cls: ObjectType) -> bool:
        if cls.__module__ != self.module.__name__:
            return False
        if self.partition is None:
            return True

        return self.partition is object_kind(cls)

    def path_to(self, cls: ObjectType | ModuleType) -> str:
        if self.partition is not None:
            kind = object_kind(cls)
        else:
            kind = None

        if isinstance(cls, ModuleType):
            module = cls
        else:
            module = sys.modules[cls.__module__]

        target = Context(module, kind).name()
        source = self.name()
        return module_path(target, source)


def module_anchor(module: ModuleType) -> str:
    "Module anchor within a Markdown file."

    assert isinstance(module, ModuleType), f"expected: module reference; got: {type(module).__name__}"
    return safe_id(module.__name__)


def module_link(module: ModuleType, context: Context) -> str:
    "Markdown link with a fully-qualified module reference."

    assert isinstance(module, ModuleType), f"expected: module reference; got: {type(module).__name__}"
    return f"[{module.__name__}]({context.path_to(module)}#{safe_id(module.__name__)})"


def class_anchor(cls: type) -> str:
    "Class function anchor within a Markdown file."

    assert not isinstance(cls, ModuleType) and not is_function(cls), f"expected: class reference; got: {type(cls).__name__}"  # type: ignore[unreachable]
    return safe_id(f"{cls.__module__}.{cls.__qualname__}")


def _class_link(cls: ObjectType, context: Context, text: str | None = None) -> str:
    "Markdown link with a partially- or fully-qualified class or function reference."

    qualname = f"{cls.__module__}.{cls.__qualname__}"
    local_link = f"#{safe_id(qualname)}"

    if context.matches(cls):
        # local reference
        link = local_link
    else:
        # non-local reference
        link = f"{context.path_to(cls)}{local_link}"

    if text is None:
        text = cls.__name__
    return f"[{safe_name(text)}]({link})"


def class_link(cls: type, context: Context) -> str:
    "Markdown link with a partially- or fully-qualified class reference."

    assert not isinstance(cls, ModuleType) and not is_function(cls), f"expected: class reference; got: {type(cls).__name__}"  # type: ignore[unreachable]
    return _class_link(cls, context)


def function_anchor(fn: CallableType) -> str:
    "Function anchor within a Markdown file."

    assert is_function(fn), f"expected: function reference; got: {type(fn).__name__}"
    return safe_id(f"{fn.__module__}.{fn.__qualname__}")


def function_link(fn: CallableType, context: Context) -> str:
    "Markdown link with a partially- or fully-qualified function reference."

    assert is_function(fn), f"expected: function reference; got: {type(fn).__name__}"
    return _class_link(fn, context)


def decorator_link(fn: CallableType, context: Context) -> str:
    "Markdown link with a partially- or fully-qualified decorator function reference."

    assert is_function(fn), f"expected: function reference; got: {type(fn).__name__}"
    return _class_link(fn, context, text=f"@{fn.__name__}")


def _extract_ref(text: str) -> str:
    "Extracts a fully-qualified reference from a reference string possibly with a custom label included."

    regex = re.compile(r"^[^<>]+<([^<>]+)>$")
    if (m := regex.match(text)) is not None:
        # :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`
        return m.group(1)
    else:
        # :class:`HTTPAdapter`
        return text


def is_private(cls: ObjectType) -> bool:
    "True if the class or function is private to the module."

    return cls.__name__.startswith("_") and not cls.__name__.startswith("__")


def is_documented(cls: ObjectType) -> bool:
    "True if the class or function has a doc-string description."

    return parse_type(cls).full_description is not None


class MarkdownWriter:
    "Writes lines to a Markdown document."

    lines: list[str]

    def __init__(self) -> None:
        self.lines = []

    def __bool__(self) -> bool:
        return len(self.lines) > 0

    def fetch(self) -> str:
        lines = "\n".join(self.lines)
        self.lines = []
        return lines

    def print(self, line: str = "") -> None:
        self.lines.append(line)


@enum.unique
class MarkdownAnchorStyle(enum.Enum):
    "Output format for generating anchors in headings."

    GITBOOK = "GitBook"
    'GitBook anchor style, with explicit HTML anchor element <a name="..."></a> in heading text.'

    GITHUB = "GitHub"
    "GitBook anchor style, with Markdown extension syntax {#...} following heading title text."


@enum.unique
class PartitionStrategy(enum.Enum):
    "Determines how to split module contents across Markdown files."

    SINGLE = "single"
    "Create a single Markdown file with all classes, enums and functions in a module."

    BY_KIND = "by_kind"
    "Create separate Markdown files for classes, enums and functions in each module."


@dataclass
class MarkdownOptions:
    """
    Options for generating Markdown output.

    :param anchor_style: Output format for generating anchors in headings.
    :param partition_strategy: Determines how to split module contents across Markdown files.
    :param include_private: Whether to include private classes, functions and methods.
    :param include_undocumented: Whether to include classes, functions and methods without a doc-string description.
    :param stdlib_links: Whether to include references for built-in types and types in the Python standard library.
    """

    anchor_style: MarkdownAnchorStyle = MarkdownAnchorStyle.GITHUB
    partition_strategy: PartitionStrategy = PartitionStrategy.SINGLE
    include_private: bool = False
    include_undocumented: bool = False
    stdlib_links: bool = True


class ProcessingError(RuntimeError):
    """
    Raised when inspecting a class or function fails.

    :param obj: The class or function object that triggered the error.
    """

    obj: type

    def __init__(self, *args: Any, obj: type) -> None:
        super().__init__(*args)
        self.obj = obj


class MarkdownTypeFormatter:
    "Generates a safe Markdown string from a Python type."

    formatter: TypeFormatter

    def __init__(self, module: ModuleType, type_transform: Callable[[type], str]) -> None:
        """
        Creates a type formatter.

        :param module: The module in whose context forward references are evaluated.
        :param type_transform: Transformation to apply to types before a string is emitted, e.g. to create a link in a documentation.
        """

        self.formatter = TypeFormatter(
            context=module,
            type_transform=type_transform,
            value_transform=quote_value,
            use_union_operator=True,
        )

    def type_to_markdown(self, data_type: TypeLike) -> str:
        "Emits a safe Markdown string for a data type."

        return self.formatter.python_type_to_str(data_type).replace("[[", "[&#x200B;[").replace("]]", "]&#x200B;]")


class MarkdownGenerator:
    "Generates Markdown documentation for a list of modules."

    modules: list[ModuleType]
    options: MarkdownOptions
    predicate: Callable[[ObjectType], bool] | None

    def __init__(
        self,
        modules: list[ModuleType],
        *,
        options: MarkdownOptions | None = None,
        predicate: Callable[[ObjectType], bool] | None = None,
    ) -> None:
        """
        Instantiates a Markdown generator object.

        :param options: Options for generating Markdown output.
        :param predicate: If given, only those classes and functions are processed for which the predicate returns `True`.
        """

        self.modules = modules
        self.options = options if options is not None else MarkdownOptions()
        self.predicate = predicate

    def _heading_anchor(self, anchor: str, text: str) -> str:
        """
        Creates an anchor in a heading.

        :param anchor: Anchor name, following HTML and Markdown identifier rules.
        :param text: Heading title text.
        """

        match self.options.anchor_style:
            case MarkdownAnchorStyle.GITHUB:
                return f'<a name="{anchor}"></a> {text}'
            case MarkdownAnchorStyle.GITBOOK:
                return text + " {#" + anchor + "}"

    def _module_link(self, module: ModuleType, context: Context) -> str:
        "Creates a link to a class if it is part of the exported batch."

        if module in self.modules:
            return module_link(module, context)
        else:
            return safe_name(module.__name__)

    def _class_link(self, cls: type, context: Context) -> str:
        "Creates a link to a class if it is part of the exported batch."

        if cls.__module__ == "builtins":
            if issubclass(cls, BaseException):
                return f"[{cls.__name__}](https://docs.python.org/3/library/exceptions.html#{cls.__name__})"

            # built-in type such as `bool`, `int` or `str`
            return cls.__name__
        elif self.options.stdlib_links and (cls.__module__ in sys.builtin_module_names or cls.__module__ in sys.stdlib_module_names):
            # standard library reference
            qualname = f"{cls.__module__}.{cls.__qualname__}"
            return f"[{qualname}](https://docs.python.org/3/library/{cls.__module__}.html#{qualname})"

        module = sys.modules[cls.__module__]
        if module in self.modules:
            return class_link(cls, context)
        else:
            return safe_name(cls.__name__)

    def _decorator_link(self, fn: CallableType, context: Context) -> str:
        "Creates a link to a decorator function if it is part of the exported batch."

        module = sys.modules[fn.__module__]
        if module in self.modules:
            return decorator_link(fn, context)
        else:
            return f"@{safe_name(fn.__name__)}"

    def _function_link(self, fn: CallableType, context: Context) -> str:
        "Creates a link to a function if it is part of the exported batch."

        module = sys.modules[fn.__module__]
        if module in self.modules:
            return function_link(fn, context)
        else:
            return safe_name(fn.__name__)

    def _replace_refs(self, text: str, resolver: Resolver, context: Context) -> str:
        "Replaces references in module, class or parameter doc-string text."

        def _replace_module_ref(m: re.Match[str]) -> str:
            ref: str = _extract_ref(m.group(1))
            obj: Any = resolver.evaluate(ref)
            if not isinstance(obj, ModuleType):
                raise ValueError(f"expected: module reference; got: {obj} of type {type(obj)}")
            return self._module_link(obj, context)

        def _replace_class_ref(m: re.Match[str]) -> str:
            ref = _extract_ref(m.group(1))
            obj: Any = resolver.evaluate(ref)
            if isinstance(obj, ModuleType) or is_function(obj) or not isinstance(obj, type):
                raise ValueError(f"expected: class reference; got: {obj} of type {type(obj)}")
            return self._class_link(obj, context)

        def _replace_deco_ref(m: re.Match[str]) -> str:
            ref: str = _extract_ref(m.group(1))
            obj: Any = resolver.evaluate(ref)
            if not is_function(obj):
                raise ValueError(f"expected: decorator reference; got: {obj} of type {type(obj)}")
            return self._decorator_link(obj, context)

        def _replace_func_ref(m: re.Match[str]) -> str:
            ref: str = _extract_ref(m.group(1))
            obj: Any = resolver.evaluate(ref)
            if not is_function(obj):
                raise ValueError(f"expected: function reference; got: {obj} of type {type(obj)}")
            return self._function_link(obj, context)

        regex = re.compile(r":mod:`([^`]+)`")
        text = regex.sub(_replace_module_ref, text)

        regex = re.compile(r":class:`([^`]+)`")
        text = regex.sub(_replace_class_ref, text)

        regex = re.compile(r":exc:`([^`]+)`")
        text = regex.sub(_replace_class_ref, text)

        regex = re.compile(r":deco:`([^`]+)`")
        text = regex.sub(_replace_deco_ref, text)

        regex = re.compile(r":func:`([^`]+)`")
        text = regex.sub(_replace_func_ref, text)

        regex = re.compile(r":meth:`([^`]+)`")
        text = regex.sub(_replace_func_ref, text)

        return text

    def _transform_text(self, text: str, resolver: Resolver, context: Context) -> str:
        """
        Applies transformations to module, class or parameter doc-string text.

        :param text: Text to apply transformations to.
        :param resolver: Resolves references to their corresponding Python types.
        :param context: The module in which the transformation is operating, used to shorten local links.
        """

        text = text.strip()
        text = replace_links(text)
        text = self._replace_refs(text, resolver, context)
        return text

    def _create_context(self, module: ModuleType, partition: ObjectKind) -> Context:
        match self.options.partition_strategy:
            case PartitionStrategy.SINGLE:
                return Context(module, None)
            case PartitionStrategy.BY_KIND:
                return Context(module, partition)

    def _generate_enum(self, cls: type[Enum], w: MarkdownWriter) -> None:
        "Writes Markdown output for a single Python enumeration class with all enumeration members."

        module = sys.modules[cls.__module__]
        docstring = parse_type(cls)
        description = docstring.full_description
        if description:
            w.print(self._transform_text(description, ClassResolver(cls), self._create_context(module, ObjectKind.ENUM)))
            w.print()

        w.print("**Members:**")
        w.print()
        try:
            labels = enum_labels(cls)
            for e in cls:
                enum_def = f"* **{safe_name(e.name)}** = {quote_value(e.value)}"
                enum_label = labels.get(e.name)
                if enum_label is not None:
                    w.print(f"{enum_def} - {enum_label}")
                else:
                    w.print(enum_def)
        except OSError:  # source code not available
            # some special constructs (e.g. dynamically generated code) don't have source
            for e in cls:
                enum_def = f"* **{safe_name(e.name)}** = {quote_value(e.value)}"
                w.print(enum_def)

        w.print()

    def _generate_bases(self, cls: type, w: MarkdownWriter) -> None:
        "Writes base classes for a Python class."

        module = sys.modules[cls.__module__]
        bases = [b for b in cls.__bases__ if b is not object]
        context = self._create_context(module, ObjectKind.CLASS)
        if len(bases) > 0:
            w.print(f"**Bases:** {', '.join(self._class_link(b, context) for b in bases)}")
            w.print()

    def _generate_references(self, references: list[DocstringSeeAlso], w: MarkdownWriter) -> None:
        "Writes references defined in a doc-string with `:see:`."

        if references:
            w.print("**References:**")
            w.print()
            for reference in references:
                w.print(f"* {reference.text}")
            w.print()

    def _generate_function(
        self,
        function: CallableType,
        signature_resolver: Resolver,
        param_resolver: Resolver,
        context: Context,
        fmt: MarkdownTypeFormatter,
        w: MarkdownWriter,
    ) -> None:
        "Writes Markdown output for a single Python function."

        docstring = parse_type(function)
        description = docstring.full_description

        signature = inspect.signature(function)
        func_params: list[str] = []
        for param_name, param in signature.parameters.items():
            if param.annotation is not inspect.Signature.empty:
                param_type = fmt.type_to_markdown(param.annotation)
                func_params.append(f"{param_name}: {param_type}")
            else:
                func_params.append(param_name)
        param_list = ", ".join(func_params)
        if signature.return_annotation is not inspect.Signature.empty:
            function_returns = fmt.type_to_markdown(signature.return_annotation)
            returns = f" → {function_returns}"
        else:
            returns = ""
        title = f"{safe_name(function.__name__)} ( {param_list} ){returns}"
        w.print(f"### {self._heading_anchor(function_anchor(function), title)}")
        w.print()

        if description:
            w.print(self._transform_text(description, signature_resolver, context))
            w.print()

        if docstring.params:
            w.print("**Parameters:**")
            w.print()

            for param_name, docstring_param in docstring.params.items():
                param_item = f"**{safe_name(param_name)}**"
                param_desc = self._transform_text(docstring_param.description, param_resolver, context)
                if docstring_param.param_type is not inspect.Signature.empty:
                    param_type = fmt.type_to_markdown(docstring_param.param_type)
                    w.print(f"* {param_item} ({param_type}) - {param_desc}")
                else:
                    w.print(f"* {param_item} - {param_desc}")
            w.print()

        if docstring.returns:
            returns_desc = self._transform_text(docstring.returns.description, param_resolver, context)
            if docstring.returns.return_type is not inspect.Signature.empty:
                return_type = fmt.type_to_markdown(docstring.returns.return_type)
                w.print(f"**Returns:** ({return_type}) - {returns_desc}")
            else:
                w.print(f"**Returns:** {returns_desc}")
            w.print()

        self._generate_references(docstring.see_also, w)

    def _generate_functions(self, cls: type, fmt: MarkdownTypeFormatter, w: MarkdownWriter) -> None:
        "Writes Markdown output for Python member functions in a class."

        for name, func in inspect.getmembers(cls, lambda f: is_function(f)):
            # skip inherited functions (unless overridden)
            if name not in cls.__dict__:
                continue

            # skip private functions
            if not self.options.include_private and is_private(func):
                continue

            # skip functions without documentation
            if not self.options.include_undocumented and not is_documented(func):
                continue

            module = sys.modules[func.__module__]
            context = self._create_context(module, ObjectKind.CLASS)
            self._generate_function(func, ClassResolver(cls), MemberFunctionResolver(cls, func), context, fmt, w)  # pyright: ignore[reportArgumentType]

    def _generate_class(self, cls: type, w: MarkdownWriter) -> None:
        "Writes Markdown output for a single (regular) Python class."

        self._generate_bases(cls, w)

        module = sys.modules[cls.__module__]
        context = self._create_context(module, ObjectKind.CLASS)

        fmt = MarkdownTypeFormatter(module, lambda c: self._class_link(c, context))

        docstring = parse_type(cls)
        description = docstring.full_description
        if description:
            w.print(self._transform_text(description, ClassResolver(cls), context))
            w.print()

        self._generate_references(docstring.see_also, w)

        self._generate_functions(cls, fmt, w)

    def _generate_dataclass(self, cls: type[DataclassInstance], w: MarkdownWriter) -> None:
        "Writes Markdown output for a single Python data-class."

        self._generate_bases(cls, w)

        module = sys.modules[cls.__module__]
        context = self._create_context(module, ObjectKind.DATACLASS)

        fmt = MarkdownTypeFormatter(module, lambda c: self._class_link(c, context))

        docstring = parse_type(cls)
        if docstring.short_description or docstring.params:
            check_docstring(cls, docstring, strict=True)
        description = docstring.full_description
        if description:
            w.print(self._transform_text(description, ClassResolver(cls), context))
            w.print()

        if docstring.params:
            w.print("**Properties:**")
            w.print()

            for name, docstring_param in docstring.params.items():
                param_type = fmt.type_to_markdown(docstring_param.param_type)
                param_desc = self._transform_text(docstring_param.description, MemberResolver(cls, name), context)
                w.print(f"* **{safe_name(name)}** ({param_type}) - {param_desc}")
            w.print()

        self._generate_references(docstring.see_also, w)

        self._generate_functions(cls, fmt, w)

    def _generate_module(self, module: ModuleType, target: Path, partition: ObjectKind | None) -> None:
        "Writes Markdown output for a single Python module."

        context = self._create_context(module, ObjectKind.MODULE)
        fmt = MarkdownTypeFormatter(module, lambda c: self._class_link(c, context))

        header = MarkdownWriter()
        module_name = module.__name__.split(".")[-1]
        header.print(f"# {self._heading_anchor(module_anchor(module), module_name)}")
        header.print()

        docstring = parse_type(module)
        if docstring.full_description:
            header.print(self._transform_text(docstring.full_description, ModuleResolver(module), context))
            header.print()

        self._generate_references(docstring.see_also, header)

        w = MarkdownWriter()
        for cls in get_module_classes(module):
            if not self.options.include_private and is_private(cls):
                continue

            if self.predicate is not None and not self.predicate(cls):
                continue

            # check whether the current object is to be exported
            if partition is not None:
                if is_dataclass_type(cls):
                    if partition is not ObjectKind.DATACLASS:
                        continue
                elif is_type_enum(cls):
                    if partition is not ObjectKind.ENUM:
                        continue
                elif isinstance(cls, type):  # pyright: ignore[reportUnnecessaryIsInstance]
                    if partition is not ObjectKind.CLASS:
                        continue

            w.print(f"## {self._heading_anchor(class_anchor(cls), safe_name(cls.__name__))}")
            w.print()

            try:
                if is_dataclass_type(cls):
                    self._generate_dataclass(cls, w)
                elif is_type_enum(cls):
                    self._generate_enum(cls, w)
                elif isinstance(cls, type):  # pyright: ignore[reportUnnecessaryIsInstance]
                    self._generate_class(cls, w)
                else:
                    raise TypeError(f"expected: data-class, enum class or regular class; got: {cls}")
            except Exception as e:
                raise ProcessingError(
                    f"error while processing type `{cls.__name__}` in module `{module.__name__}`",
                    obj=cls,
                ) from e

        if partition is None or partition is ObjectKind.FUNCTION:
            # generate top-level module functions
            functions = get_module_functions(module)
            if not self.options.include_private:
                functions = [fn for fn in functions if not is_private(fn)]
            if not self.options.include_undocumented:
                functions = [fn for fn in functions if is_documented(fn)]
            if functions:
                anchor = f"{safe_id(module.__name__)}-functions"
                anchored_title = self._heading_anchor(anchor, "Functions")
                w.print(f"## {anchored_title}")
                w.print()

                for func in functions:
                    self._generate_function(func, ModuleResolver(module), ModuleFunctionResolver(func), context, fmt, w)

        if w:
            with open(target, "w", encoding="utf-8") as f:
                f.write(header.fetch())
                f.write("\n")
                f.write(w.fetch())

    def generate(self, target: Path) -> None:
        """
        Writes Markdown files to a target directory.

        The subdirectories that files are written to match the hierarchy of the Python modules.
        """

        for module in self.modules:
            module_path = module.__name__.replace(".", "/") + ".md"
            path = target / Path(module_path)
            os.makedirs(path.parent, exist_ok=True)

            match self.options.partition_strategy:
                case PartitionStrategy.SINGLE:
                    self._generate_module(module, path, None)
                case PartitionStrategy.BY_KIND:
                    for partition in [ObjectKind.DATACLASS, ObjectKind.ENUM, ObjectKind.CLASS, ObjectKind.FUNCTION]:
                        partition_path = path.with_stem(f"{path.stem}-{partition.value}")
                        self._generate_module(module, partition_path, partition)


def generate_markdown(modules: list[ModuleType], out_dir: Path, *, options: MarkdownOptions | None = None) -> None:
    """
    Generates Markdown documentation for a list of modules.

    :param modules: The list of modules to generate documentation for.
    :param out_dir: Directory to write Markdown files to.
    :param options: Options for generating Markdown output.
    """

    if not modules:
        raise ValueError("no Python module given")
    if options is None:
        options = MarkdownOptions()

    MarkdownGenerator(modules, options=options).generate(out_dir)
