"""
Generate Markdown documentation from Python code

Copyright 2024-2025, Levente Hunyadi

:see: https://github.com/hunyadi/markdown_doc
"""

import argparse
import importlib
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from .argparse_action import EnumAction
from .generator import MarkdownAnchorStyle, MarkdownOptions, PartitionStrategy, generate_markdown
from .import_util import import_modules


@dataclass
class ProgramArgs(argparse.Namespace):
    directory: list[Path]
    module: list[str]
    root_dir: Path
    out_dir: Path
    anchor_style: MarkdownAnchorStyle
    partition: PartitionStrategy


parser = argparse.ArgumentParser(
    prog=Path(__file__).parent.name,
    description="Generates Markdown documentation from Python code",
)
parser.add_argument(
    "-d",
    "--directory",
    type=Path,
    action="extend",
    nargs="*",
    help="folder(s) to recurse into when looking for modules",
)
parser.add_argument(
    "-m",
    "--module",
    action="extend",
    nargs="*",
    help="qualified names(s) of Python module(s) to scan",
)
parser.add_argument(
    "-r",
    "--root-dir",
    type=Path,
    default=Path.cwd(),
    help="path to act as root for converting directory paths into qualified module names (default: working directory)",
)
parser.add_argument(
    "-o",
    "--out-dir",
    type=Path,
    default=Path.cwd() / "docs",
    help="output directory (default: 'docs' in working directory)",
)
parser.add_argument(
    "--anchor-style",
    action=EnumAction(MarkdownAnchorStyle),  # type: ignore
    default=MarkdownAnchorStyle.GITBOOK,
    help="output format for generating anchors in headings",
)
parser.add_argument(
    "--partition",
    action=EnumAction(PartitionStrategy),  # type: ignore
    default=PartitionStrategy.SINGLE,
    help="how to split module contents across Markdown files",
)

args = parser.parse_args(namespace=ProgramArgs)
out_dir = Path.cwd() / args.out_dir  # does not alter absolute paths
root_dir = Path.cwd() / args.root_dir  # does not alter absolute paths

try:
    modules: list[ModuleType] = []
    if args.directory:
        for directory in args.directory:
            if not directory.is_dir():
                raise ValueError(f"not a directory: {directory}")

            modules.extend(import_modules(root_dir, directory))
    if args.module:
        for module in args.module:
            modules.append(importlib.import_module(module))

    options = MarkdownOptions(anchor_style=args.anchor_style)

    generate_markdown(modules, out_dir, options=options)
except Exception as e:
    print(e, file=sys.stderr)
    if e.__cause__:
        print(e.__cause__, file=sys.stderr)
    sys.exit(1)
