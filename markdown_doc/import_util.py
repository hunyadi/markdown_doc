"""
Generate Markdown documentation from Python code

Copyright 2024-2025, Levente Hunyadi

:see: https://github.com/hunyadi/markdown_doc
"""

import importlib
import os
from pathlib import Path
from types import ModuleType


def module_path(root_path: Path, abs_path: Path) -> str:
    "Qualified module name from root path and absolute path."

    return abs_path.relative_to(root_path).as_posix().replace("/", ".")


def import_modules(root_path: Path, scan_path: Path) -> list[ModuleType]:
    """
    Recurses into the specified directory to import all Python modules within.

    :param root_path: The directory to act as `PYTHONPATH`.
    :param scan_path: The sub-directory to recurse into.
    """

    root_path = root_path.absolute()
    scan_path = scan_path.absolute()
    if not scan_path.is_relative_to(root_path):
        raise ValueError("expected: a scan path relative to root path")
    if not scan_path.is_dir():
        raise ValueError("expected: a directory to scan")

    modules: list[ModuleType] = []
    for dir_path, dir_names, file_names in os.walk(str(scan_path), topdown=True):
        if "__init__.py" not in file_names:  # not a Python module
            dir_names[:] = []
            continue

        recurse_into: list[str] = []
        for dir_name in dir_names:
            if not dir_name.startswith("."):
                recurse_into.append(dir_name)
        dir_names[:] = recurse_into

        # import self
        base_path = Path(dir_path)
        qualified_name = module_path(root_path, base_path)
        try:
            module = importlib.import_module(qualified_name)
            modules.append(module)
        except ModuleNotFoundError:
            pass

        # import child modules
        for file_name in file_names:
            if file_name.startswith("__") or not file_name.endswith(".py"):
                continue

            qualified_name = module_path(root_path, base_path / file_name.removesuffix(".py"))
            try:
                module = importlib.import_module(qualified_name)
                modules.append(module)
            except ModuleNotFoundError:
                pass

    return modules
