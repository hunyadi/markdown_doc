import abc
import ast
import inspect
import logging
import os
import re
import sys
import typing
from enum import Enum
from pathlib import Path
from types import FunctionType, ModuleType

from strong_typing.docstring import check_docstring, parse_type
from strong_typing.inspection import (
    DataclassInstance,
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


def safe_name(name: str) -> str:
    "Object name with those characters escaped that are allowed in Python identifiers but have special meaning in Markdown."

    return name.replace("_", "\\_")


def safe_id(name: str) -> str:
    "Object identifier that qualifies as a Markdown anchor."

    parts = name.split(".")
    return ".".join(
        (part if not part.startswith("__") else f"sp{part}") for part in parts
    )


def module_path(target: str, source: str) -> str:
    target_path = Path("/" + target.replace(".", "/") + ".md")
    source_path = Path("/" + source.replace(".", "/") + ".md")
    target_dir = target_path.parent
    source_dir = source_path.parent
    return (
        Path(target_dir).relative_to(source_dir, walk_up=True) / target_path.name
    ).as_posix()


def module_anchor(module: ModuleType) -> str:
    "Module anchor within a Markdown file."

    return f"{{#{safe_id(module.__name__)}}}"


def module_link(module: ModuleType, context: ModuleType) -> str:
    "Markdown link with a fully-qualified module reference."

    return f"[{module.__name__}]({module_path(module.__name__, context.__name__)}#{safe_id(module.__name__)})"


def class_anchor(cls: type) -> str:
    "Class or function anchor within a Markdown file."

    qualname = f"{cls.__module__}.{cls.__qualname__}"
    return f"{{#{safe_id(qualname)}}}"


def class_link(cls: type, context: ModuleType) -> str:
    "Markdown link with a partially- or fully-qualified class or function reference."

    qualname = f"{cls.__module__}.{cls.__qualname__}"
    local_link = f"#{safe_id(qualname)}"
    if cls.__module__ != context.__name__:
        # non-local reference
        link = f"{module_path(cls.__module__, context.__name__)}{local_link}"
    else:
        # local reference
        link = local_link

    return f"[{safe_name(cls.__name__)}]({link})"


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


class Resolver(abc.ABC):
    "Translates string references to the corresponding Python type within the context of an encapsulating type."

    @abc.abstractmethod
    def evaluate(self, ref: str) -> type: ...

    def evaluate_global(self, ref: str) -> type | None:
        try:
            # evaluate as fully-qualified reference in each loaded module
            for name, module in sys.modules.items():
                if ref == name:
                    return typing.cast(type, module)
                prefix = f"{name}."
                if ref.startswith(prefix):
                    return eval(ref.removeprefix(prefix), module.__dict__, locals())
        except NameError:
            pass

        return None


class ModuleResolver(Resolver):
    "A resolver that operates within the top-level context of a module."

    module: ModuleType

    def __init__(self, module: ModuleType):
        super().__init__()
        self.module = module

    def _evaluate(self, ref: str) -> type | None:
        obj = self.evaluate_global(ref)
        if obj is not None:
            return obj

        try:
            # evaluate as module-local reference
            return eval(ref, self.module.__dict__, locals())
        except NameError:
            pass

        return None

    def evaluate(self, ref: str) -> type:
        obj = self._evaluate(ref)
        if obj is not None:
            return obj

        raise DocumentationError(
            f"`{ref}` is not defined in the context of module `{self.module.__name__}`"
        )


class ClassResolver(Resolver):
    "A resolver that operates within the context of a class."

    cls: type

    def __init__(self, cls: type):
        super().__init__()
        self.cls = cls

    def _evaluate(self, ref: str) -> type | None:
        obj = self.evaluate_global(ref)
        if obj is not None:
            return obj

        try:
            # evaluate as module-local reference
            module = sys.modules[self.cls.__module__]
            return eval(ref, module.__dict__, locals())
        except NameError:
            pass

        try:
            # evaluate as class-local reference
            return eval(ref, dict(self.cls.__dict__), locals())
        except NameError:
            pass

        return None

    def evaluate(self, ref: str) -> type:
        obj = self._evaluate(ref)
        if obj is not None:
            return obj

        raise DocumentationError(
            f"`{ref}` is not defined in the context of class `{self.cls.__name__}` in module `{self.cls.__module__}`"
        )


class MemberResolver(ClassResolver):
    "A resolver that operates within the context of a member property of a class."

    member_name: str

    def __init__(self, cls: type, member_name: str):
        super().__init__(cls)
        self.member_name = member_name

    def evaluate(self, ref: str) -> type:
        obj = self._evaluate(ref)
        if obj is not None:
            return obj

        raise DocumentationError(
            f"`{ref}` is not defined in the context of member `{self.member_name}` in class `{self.cls.__name__}` in module `{self.cls.__module__}`"
        )


class FunctionResolver(ClassResolver):
    "A resolver that operates within the context of a member function of a class."

    func_name: str

    def __init__(self, cls: type, func_name: str):
        super().__init__(cls)
        self.func_name = func_name

    def evaluate(self, ref: str) -> type:
        obj = self._evaluate(ref)
        if obj is not None:
            return obj

        raise DocumentationError(
            f"`{ref}` is not defined in the context of function `{self.func_name}` in class `{self.cls.__name__}` in module `{self.cls.__module__}`"
        )


class MarkdownWriter:
    "Writes lines to a Markdown document."

    lines: list[str]

    def __init__(self) -> None:
        self.lines = []

    def print(self, line: str = "") -> None:
        self.lines.append(line)


class MarkdownGenerator:
    "Generates Markdown documentation for a list of modules."

    modules: list[ModuleType]

    def __init__(self, modules: list[ModuleType]) -> None:
        self.modules = modules

    def _module_link(self, module: ModuleType, context: ModuleType) -> str:
        "Creates a link to a class if it is part of the exported batch."

        if module in self.modules:
            return module_link(module, context)
        else:
            return safe_name(module.__name__)

    def _replace_module_ref(
        self, m: re.Match[str], resolver: Resolver, context: ModuleType
    ) -> str:
        ref: str = m.group(1)
        obj = resolver.evaluate(ref)
        if not isinstance(obj, ModuleType):
            raise ValueError(
                f"expected: module reference; got: {obj} of type {type(obj)}"
            )
        return self._module_link(obj, context)

    def _class_link(self, cls: type, context: ModuleType) -> str:
        "Creates a link to a class if it is part of the exported batch."

        module = sys.modules[cls.__module__]
        if module in self.modules:
            return class_link(cls, context)
        else:
            return safe_name(cls.__name__)

    def _replace_class_ref(
        self, m: re.Match[str], resolver: Resolver, context: ModuleType
    ) -> str:
        ref: str = m.group(1)
        obj = resolver.evaluate(ref)
        if isinstance(obj, ModuleType) or isinstance(obj, FunctionType):
            raise ValueError(
                f"expected: class reference; got: {obj} of type {type(obj)}"
            )
        return self._class_link(obj, context)

    def _replace_func_ref(
        self, m: re.Match[str], resolver: Resolver, context: ModuleType
    ) -> str:
        ref: str = m.group(1)
        obj = resolver.evaluate(ref)
        if not isinstance(obj, FunctionType):
            raise ValueError(
                f"expected: function reference; got: {obj} of type {type(obj)}"
            )
        return self._class_link(obj, context)

    def _replace_refs(self, text: str, resolver: Resolver, context: ModuleType) -> str:
        "Replaces references in module, class or parameter doc-string text."

        regex = re.compile(r":mod:`([^`]+)`")
        text = regex.sub(lambda m: self._replace_module_ref(m, resolver, context), text)

        regex = re.compile(r":class:`([^`]+)`")
        text = regex.sub(lambda m: self._replace_class_ref(m, resolver, context), text)

        regex = re.compile(r":meth:`([^`]+)`")
        text = regex.sub(lambda m: self._replace_func_ref(m, resolver, context), text)

        return text

    def _transform_text(
        self, text: str, resolver: Resolver, context: ModuleType
    ) -> str:
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

    def _generate_enum(self, cls: type[Enum], w: MarkdownWriter) -> None:
        module = sys.modules[cls.__module__]
        docstring = parse_type(cls)
        description = docstring.full_description
        if description:
            w.print(self._transform_text(description, ClassResolver(cls), module))
            w.print()

        labels = enum_labels(cls)
        w.print("**Members:**")
        w.print()
        for e in cls:
            enum_def = f"* **{safe_name(e.name)}** = `{repr(e.value)}`"
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

    def _generate_functions(self, cls: type, w: MarkdownWriter) -> None:
        module = sys.modules[cls.__module__]

        fmt = TypeFormatter(
            context=module,
            type_transform=lambda c: self._class_link(c, module),
            use_union_operator=True,
        )

        for func_name, func in inspect.getmembers(cls, lambda f: inspect.isfunction(f)):
            docstring = parse_type(func)

            description = docstring.full_description
            if not description:
                continue

            func_params: list[str] = []
            for param in docstring.params.values():
                param_type = fmt.python_type_to_str(param.param_type)
                func_params.append(f"{param.name}: {param_type}")
            param_list = ", ".join(func_params)
            if docstring.returns:
                func_returns = fmt.python_type_to_str(docstring.returns.return_type)
                returns = f" → {func_returns}"
            else:
                returns = ""
            w.print(
                f"### {safe_name(func_name)} ( {param_list} ){returns} {class_anchor(func)}"
            )
            w.print()

            w.print(self._transform_text(description, ClassResolver(cls), module))
            w.print()

            if docstring.params:
                w.print("**Parameters:**")
                w.print()

                for param_name, param in docstring.params.items():
                    param_type = fmt.python_type_to_str(param.param_type)
                    param_desc = self._transform_text(
                        param.description, FunctionResolver(cls, func_name), module
                    )
                    w.print(
                        f"* **{safe_name(param_name)}** ({param_type}) - {param_desc}"
                    )
                w.print()

    def _generate_class(self, cls: type, w: MarkdownWriter) -> None:
        self._generate_bases(cls, w)

        module = sys.modules[cls.__module__]
        docstring = parse_type(cls)
        description = docstring.full_description
        if description:
            w.print(self._transform_text(description, ClassResolver(cls), module))
            w.print()

        self._generate_functions(cls, w)

    def _generate_dataclass(
        self, cls: type[DataclassInstance], w: MarkdownWriter
    ) -> None:
        self._generate_bases(cls, w)

        module = sys.modules[cls.__module__]
        docstring = parse_type(cls)
        check_docstring(cls, docstring, strict=True)
        description = docstring.full_description
        if description:
            w.print(self._transform_text(description, ClassResolver(cls), module))
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
                param_desc = self._transform_text(
                    param.description, MemberResolver(cls, name), module
                )
                w.print(f"* **{safe_name(name)}** ({param_type}) - {param_desc}")
            w.print()

        self._generate_functions(cls, w)

    def _generate_module(self, module: ModuleType, target: Path) -> None:
        w = MarkdownWriter()
        w.print(f"# {module.__name__} {module_anchor(module)}")
        w.print()
        if module.__doc__:
            w.print(
                self._transform_text(module.__doc__, ModuleResolver(module), module)
            )
            w.print()

        for cls in get_module_classes(module):
            w.print(f"## {safe_name(cls.__name__)} {class_anchor(cls)}")
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
        for module in self.modules:
            module_path = module.__name__.replace(".", "/") + ".md"
            path = target / Path(module_path)
            os.makedirs(path.parent, exist_ok=True)
            self._generate_module(module, path)
