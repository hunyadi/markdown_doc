"""
Generate Markdown documentation from Python code

Copyright 2024, Levente Hunyadi

:see: https://github.com/hunyadi/markdown_doc
"""

import abc
import sys
import typing
from types import ModuleType


class ResolverError(RuntimeError):
    pass


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

        raise ResolverError(f"`{ref}` is not defined in the context of module `{self.module.__name__}`")


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

        raise ResolverError(f"`{ref}` is not defined in the context of class `{self.cls.__name__}` in module `{self.cls.__module__}`")


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

        raise ResolverError(
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

        raise ResolverError(
            f"`{ref}` is not defined in the context of function `{self.func_name}` in class `{self.cls.__name__}` in module `{self.cls.__module__}`"
        )
