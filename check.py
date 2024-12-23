from pathlib import Path

from markdown_doc.generator import MarkdownAnchorStyle, MarkdownGenerator, MarkdownOptions
from markdown_doc.import_util import import_modules

modules = import_modules(Path.cwd(), Path("markdown_doc"))
options = MarkdownOptions(anchor_style=MarkdownAnchorStyle.GITBOOK, include_private=True)
MarkdownGenerator(modules, options=options).generate(Path.cwd() / "output")
