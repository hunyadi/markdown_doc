from pathlib import Path

import sample.example
from markdown_doc.generator import MarkdownAnchorStyle, MarkdownGenerator, MarkdownOptions, PartitionStrategy
from markdown_doc.import_util import import_modules
from sample.auxiliary import AUXILIARY_TYPES

modules = import_modules(Path.cwd(), Path("markdown_doc"))
modules.append(sample.example)
options = MarkdownOptions(
    anchor_style=MarkdownAnchorStyle.GITBOOK,
    partition_strategy=PartitionStrategy.SINGLE,
    include_private=True,
    stdlib_links=True,
    auxiliary_types=AUXILIARY_TYPES,
)
MarkdownGenerator(modules, options=options).generate(Path.cwd() / "docs")
