"""
Generate Markdown documentation from Python code

Copyright 2024-2025, Levente Hunyadi

:see: https://github.com/hunyadi/markdown_doc
"""

import abc
import sys
import typing
from types import FunctionType, MethodType, ModuleType


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
                    return typing.cast(type, eval(ref.removeprefix(prefix), module.__dict__, locals()))
        except NameError:
            pass

        return None


class ModuleResolver(Resolver):
    "A resolver that operates within the top-level context of a module."

    module: ModuleType

    def __init__(self, module: ModuleType) -> None:
        super().__init__()
        self.module = module

    def _evaluate(self, ref: str) -> type | None:
        obj = self.evaluate_global(ref)
        if obj is not None:
            return obj

        try:
            # evaluate as module-local reference
            return typing.cast(type, eval(ref, self.module.__dict__, locals()))
        except NameError:
            pass

        return None

    def evaluate(self, ref: str) -> type:
        obj = self._evaluate(ref)
        if obj is not None:
            return obj

        raise ResolverError(f"`{ref}` is not defined in the context of module `{self.module.__name__}`")


class ModuleFunctionResolver(ModuleResolver):
    "A resolver that operates within the context of a module-level function."

    function: FunctionType

    def __init__(self, function: FunctionType) -> None:
        super().__init__(sys.modules[function.__module__])
        self.function = function  # type: ignore

    def evaluate(self, ref: str) -> type:
        obj = self._evaluate(ref)
        if obj is not None:
            return obj

        raise ResolverError(f"`{ref}` is not defined in the context of function `{self.function.__name__}` in module `{self.function.__module__}`")


class ClassResolver(Resolver):
    "A resolver that operates within the context of a class."

    cls: type

    def __init__(self, cls: type) -> None:
        super().__init__()
        self.cls = cls

    def _evaluate(self, ref: str) -> type | None:
        obj = self.evaluate_global(ref)
        if obj is not None:
            return obj

        try:
            # evaluate as module-local reference
            module = sys.modules[self.cls.__module__]
            return typing.cast(type, eval(ref, module.__dict__, locals()))
        except NameError:
            pass

        try:
            # evaluate as class-local reference
            return typing.cast(type, eval(ref, dict(self.cls.__dict__), locals()))
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

    def __init__(self, cls: type, member_name: str) -> None:
        super().__init__(cls)
        self.member_name = member_name

    def evaluate(self, ref: str) -> type:
        obj = self._evaluate(ref)
        if obj is not None:
            return obj

        raise ResolverError(
            f"`{ref}` is not defined in the context of member `{self.member_name}` in class `{self.cls.__name__}` in module `{self.cls.__module__}`"
        )


class MemberFunctionResolver(ClassResolver):
    "A resolver that operates within the context of a member function of a class."

    function: MethodType

    def __init__(self, cls: type, function: MethodType) -> None:
        super().__init__(cls)
        self.function = function

    def evaluate(self, ref: str) -> type:
        obj = self._evaluate(ref)
        if obj is not None:
            return obj

        raise ResolverError(
            f"`{ref}` is not defined in the context of function `{self.function.__name__}` in class `{self.cls.__name__}` in module `{self.cls.__module__}`"
        )
