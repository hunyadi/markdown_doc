"""
Generate Markdown documentation from Python code

Copyright 2024, Levente Hunyadi

:see: https://github.com/hunyadi/markdown_doc
"""

import argparse
import importlib
from pathlib import Path

from .argparse_action import EnumAction
from .generator import MarkdownAnchorStyle, MarkdownGenerator, MarkdownOptions

parser = argparse.ArgumentParser(
    prog=Path(__file__).parent.name,
    description="Generates Markdown documentation from Python code",
)
parser.add_argument("module", nargs="+", help="Python module(s) to scan for signatures and doc-strings")
parser.add_argument("-o", "--out-dir", type=Path, default="output", help="output directory")
parser.add_argument(
    "--anchor-style",
    action=EnumAction(MarkdownAnchorStyle),
    default=MarkdownAnchorStyle.GITBOOK,
    help="output format for generating anchors in headings",
)

args = parser.parse_args()
out_dir = Path.cwd() / args.out_dir
modules = [importlib.import_module(module) for module in args.module]
MarkdownGenerator(modules, options=MarkdownOptions(anchor_style=args.anchor_style)).generate(out_dir)
