import argparse
import importlib
from pathlib import Path

from .generator import MarkdownGenerator

parser = argparse.ArgumentParser(
    prog=Path(__file__).parent.name,
    description="Generates Markdown documentation from Python code",
)
parser.add_argument(
    "module", nargs="+", help="Python module(s) to scan for signatures and doc-strings"
)
parser.add_argument(
    "-o", "--out-dir", type=Path, default="output", help="output directory"
)

args = parser.parse_args()
out_dir = Path.cwd() / args.out_dir
modules = [importlib.import_module(module) for module in args.module]
MarkdownGenerator(modules).generate(out_dir)
