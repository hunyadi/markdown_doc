# Generate Markdown documentation from Python code

This library generates Markdown documentation directly from Python code.

## Features

* Each module produces a Markdown file.
* [Documentation strings](https://docs.python.org/3/library/stdtypes.html#definition.__doc__) are extracted from module, class, enumeration and function definitions.
* Cross-references work across modules.
* Data-class member descriptions (`:param ...:`) are validated if they have a matching member variable declaration.
* All enumeration members are published, even if they lack a description.
* Magic methods (e.g. `__eq__`) are published if they have a doc-string.
* Multi-line code blocks in doc-strings are retained as Markdown code blocks.
* Forward-references and type annotations as strings are automatically evaluated.

## Usage

### Python

```python
from markdown_doc.generator import MarkdownGenerator

MarkdownGenerator([module1, module2, module3]).generate(out_dir)
```

### Command line

```
$ python3 -m markdown_doc --help
usage: markdown_doc [-h] [-o OUT_DIR] module [module ...]

Generates Markdown documentation from Python code

positional arguments:
  module                Python module(s) to scan for signatures and doc-strings

options:
  -h, --help            show this help message and exit
  -o OUT_DIR, --out-dir OUT_DIR
                        output directory
```

## Related work

In order to reduce added complexity, this library does not use the Sphinx framework with [autodoc](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html).
