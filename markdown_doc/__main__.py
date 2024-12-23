"""
Generate Markdown documentation from Python code

Copyright 2024, Levente Hunyadi

:see: https://github.com/hunyadi/markdown_doc
"""

import argparse
import importlib
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from .argparse_action import EnumAction
from .generator import MarkdownAnchorStyle, MarkdownGenerator, MarkdownOptions
from .import_util import import_modules


@dataclass
class ProgramArgs(argparse.Namespace):
    directory: list[Path]
    module: list[str]
    out_dir: Path
    anchor_style: MarkdownAnchorStyle


parser = argparse.ArgumentParser(
    prog=Path(__file__).parent.name,
    description="Generates Markdown documentation from Python code",
)
parser.add_argument("-d", "--directory", type=Path, nargs="*", help="folder(s) to recurse into when looking for modules")
parser.add_argument("-m", "--module", nargs="*", help="qualified names(s) of Python module(s) to scan")
parser.add_argument("-o", "--out-dir", type=Path, default=Path.cwd() / "output", help="output directory")
parser.add_argument(
    "--anchor-style",
    action=EnumAction(MarkdownAnchorStyle),  # type: ignore
    default=MarkdownAnchorStyle.GITBOOK,
    help="output format for generating anchors in headings",
)

args = parser.parse_args(namespace=ProgramArgs)
out_dir = Path.cwd() / args.out_dir

modules: list[ModuleType] = []
if args.directory:
    for directory in args.directory:
        modules.extend(import_modules(Path.cwd(), directory))
if args.module:
    for module in args.module:
        modules.append(importlib.import_module(module))

MarkdownGenerator(modules, options=MarkdownOptions(anchor_style=args.anchor_style)).generate(out_dir)
