import ast
import inspect
import logging
import os
import re
import sys
from enum import Enum
from pathlib import Path
from types import ModuleType

from strong_typing.docstring import check_docstring, parse_type
from strong_typing.inspection import (
    DataclassInstance,
    evaluate_type,
    get_module_classes,
    is_dataclass_type,
    is_type_enum,
)
from strong_typing.name import TypeFormatter


class DocumentationError(RuntimeError):
    pass


def replace_links(text: str) -> str:
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
            [^\s`!()\[\]{};:'".,<>?«»“”‘’] # not a space or one of these punct chars
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


def module_id(name: str) -> str:
    return name if name != "__main__" else "MAIN"


def module_anchor(module: ModuleType) -> str:
    "Module anchor within a Markdown file."

    return f"{{#{module_id(module.__name__)}}}"


def module_link(module: ModuleType) -> str:
    "Markdown link with fully-qualified module reference."

    return f"[{module.__name__}]({module.__name__}.md#{module_id(module.__name__)})"


def class_anchor(cls: type) -> str:
    "Class anchor within a Markdown file."

    return f"{{#{module_id(cls.__module__)}.{cls.__name__}}}"


def class_link(cls: type, context: ModuleType) -> str:
    "Markdown link with fully-qualified class reference."

    local_link = f"#{module_id(cls.__module__)}.{cls.__name__}"
    if context.__name__ != cls.__module__:
        link = f"{cls.__module__}.md{local_link}"
    else:
        link = local_link

    return f"[{cls.__name__}]({link})"


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


class MarkdownWriter:
    lines: list[str]

    def __init__(self) -> None:
        self.lines = []

    def print(self, line: str = "") -> None:
        self.lines.append(line)


class MarkdownGenerator:
    modules: list[ModuleType]

    def __init__(self, modules: list[ModuleType]) -> None:
        self.modules = modules

    def _class_link(self, cls: type, context: ModuleType) -> str:
        module = sys.modules[cls.__module__]
        if module in self.modules:
            return class_link(cls, context)
        else:
            return cls.__name__

    def _replace_ref(self, m: re.Match, context: ModuleType) -> str:
        ref = m.group(1)

        try:
            # evaluate as fully-qualified reference
            cls: type = eval(ref)
        except NameError:
            # evaluate as module-local reference
            cls = evaluate_type(ref, context)

        return self._class_link(cls, context)

    def _replace_refs(self, text: str, context: ModuleType) -> str:
        "Replaces references in module, class or parameter doc-string text."

        regex = re.compile(r":class:`([^`]+)`", re.UNICODE)
        return regex.sub(lambda m: self._replace_ref(m, context), text)

    def _transform_text(self, text: str, context: ModuleType) -> str:
        "Applies transformations to module, class or parameter doc-string text."

        text = text.strip()
        text = replace_links(text)
        text = self._replace_refs(text, context)
        return text

    def _generate_enum(self, cls: type[Enum], w: MarkdownWriter) -> None:
        module = sys.modules[cls.__module__]
        docstring = parse_type(cls)
        description = docstring.full_description
        if description:
            try:
                w.print(self._transform_text(description, module))
            except NameError as n:
                raise DocumentationError(
                    f"`{n.name}` is not defined in the context of enum class `{cls.__name__}` in module `{cls.__module__}`"
                )
            w.print()

        labels = enum_labels(cls)
        w.print("**Members:**")
        w.print()
        for e in cls:
            enum_def = f"* **{e.name}** = {repr(e.value)}"
            enum_label = labels.get(e.name)
            if enum_label is not None:
                w.print(f"{enum_def} - {enum_label}")
            else:
                w.print(enum_def)
        w.print()

    def _generate_bases(self, cls: type, w: MarkdownWriter) -> None:
        module = sys.modules[cls.__module__]
        bases = [b for b in cls.__bases__ if b is not object]
        if len(bases) > 0:
            w.print(
                f"**Bases:** {', '.join(self._class_link(b, module) for b in bases)}"
            )
            w.print()

    def _generate_class(self, cls: type, w: MarkdownWriter) -> None:
        self._generate_bases(cls, w)

        module = sys.modules[cls.__module__]
        docstring = parse_type(cls)
        description = docstring.full_description
        if description:
            try:
                w.print(self._transform_text(description, module))
            except NameError as n:
                raise DocumentationError(
                    f"`{n.name}` is not defined in the context of class `{cls.__name__}` in module `{cls.__module__}`"
                )
            w.print()

    def _generate_dataclass(
        self, cls: type[DataclassInstance], w: MarkdownWriter
    ) -> None:
        self._generate_bases(cls, w)

        module = sys.modules[cls.__module__]
        docstring = parse_type(cls)
        check_docstring(cls, docstring, strict=True)
        description = docstring.full_description
        if description:
            try:
                w.print(self._transform_text(description, module))
            except NameError as n:
                raise DocumentationError(
                    f"`{n.name}` is not defined in the context of class `{cls.__name__}` in module `{cls.__module__}`"
                )
            w.print()

        if docstring.params:
            w.print("**Properties:**")
            w.print()

            fmt = TypeFormatter(
                context=module,
                type_transform=lambda c: self._class_link(c, module),
                use_union_operator=True,
            )

            for name, param in docstring.params.items():
                param_type = fmt.python_type_to_str(param.param_type)
                try:
                    param_desc = self._transform_text(param.description, module)
                except NameError as n:
                    raise DocumentationError(
                        f"`{n.name}` is not defined in the context of member `{name}` in class `{cls.__name__}` in module `{cls.__module__}`"
                    )
                w.print(f"* **{name}** ({param_type}) - {param_desc}")
            w.print()

    def _generate_module(self, module: ModuleType, target: Path) -> None:
        w = MarkdownWriter()
        w.print(f"# {module.__name__} {module_anchor(module)}")
        w.print()
        if module.__doc__:
            w.print(self._transform_text(module.__doc__, module))
            w.print()

        for cls in get_module_classes(module):
            w.print(f"## {cls.__name__} {class_anchor(cls)}")
            w.print()

            if is_dataclass_type(cls):
                self._generate_dataclass(cls, w)
            elif is_type_enum(cls):
                self._generate_enum(cls, w)
            elif isinstance(cls, type):
                self._generate_class(cls, w)

        with open(target, "w", encoding="utf-8") as f:
            f.write("\n".join(w.lines))

    def generate(self, target: Path) -> None:
        os.makedirs(target, exist_ok=True)
        for module in self.modules:
            self._generate_module(module, target / f"{module.__name__}.md")
