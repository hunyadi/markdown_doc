from pathlib import Path

import sample.example
from markdown_doc.generator import MarkdownAnchorStyle, MarkdownGenerator, MarkdownOptions, PartitionStrategy
from markdown_doc.import_util import import_modules

modules = import_modules(Path.cwd(), Path("markdown_doc"))
modules.append(sample.example)
options = MarkdownOptions(
    anchor_style=MarkdownAnchorStyle.GITBOOK,
    partition_strategy=PartitionStrategy.SINGLE,
    include_private=True,
    stdlib_links=True,
)
MarkdownGenerator(modules, options=options).generate(Path.cwd() / "docs")
