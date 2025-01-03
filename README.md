# Generate Markdown documentation from Python code

This library generates Markdown documentation directly from Python code, utilizing Python type annotations.

## Features at a glance

* Each module produces a Markdown file.
* [Documentation strings](https://docs.python.org/3/library/stdtypes.html#definition.__doc__) are extracted from module, class, enumeration and function definitions.
* Cross-references may be local or fully qualified, and work across modules.
* Classes with member variable declarations produce member documentation.
* Data-class field descriptions are validated if they have a matching member variable declaration.
* Enumeration members are published, even if they lack a description.
* Magic methods (e.g. `__eq__`) are published if they have a doc-string.
* Multi-line code blocks in doc-strings are retained as Markdown code blocks.
* Forward-references and type annotations as strings are automatically evaluated.

## Documentation features

Cross-references with Sphinx-style syntax (`:mod:`, `:class:` and `:meth:`) are supported in module, class and function doc-strings:

```python
@dataclass
class SampleClass:
    """
    This class is extended by :class:`DerivedClass`.

    This class implements :meth:`__lt__` and :meth:`SampleClass.__gt__`.
    """
```

Class member variable and data-class field descriptions are defined with `:param ...:`:

```python
@dataclass
class DerivedClass(SampleClass):
    """
    This data-class derives from another base class.

    :param union: A union of several types.
    :param json: A complex type with type substitution.
    :param schema: A complex type without type substitution.
    """

    union: SimpleType
    json: JsonType
    schema: Schema
```

Enumeration member description follows the member value assignment:

```python
class EnumType(enum.Enum):
    enabled = "enabled"
    "Documents the enumeration member `enabled`."

    disabled = "disabled"
    "Documents the enumeration member `disabled`."
```

## Usage

### Calling the utility in Python

```python
from markdown_doc.generator import MarkdownGenerator

MarkdownGenerator([module1, module2, module3]).generate(out_dir)
```

### Running the utility from the command line

```
$ python3 -m markdown_doc --help
usage: markdown_doc [-h] [-d [DIRECTORY ...]] [-m [MODULE ...]] [-r ROOT_DIR] [-o OUT_DIR] [--anchor-style {GitBook,GitHub}]

Generates Markdown documentation from Python code

options:
  -h, --help            show this help message and exit
  -d [DIRECTORY ...], --directory [DIRECTORY ...]
                        folder(s) to recurse into when looking for modules
  -m [MODULE ...], --module [MODULE ...]
                        qualified names(s) of Python module(s) to scan
  -r ROOT_DIR, --root-dir ROOT_DIR
                        path to act as root for converting directory paths into qualified module names (default: working directory)
  -o OUT_DIR, --out-dir OUT_DIR
                        output directory (default: 'docs' in working directory)
  --anchor-style {GitBook,GitHub}
                        output format for generating anchors in headings
```

## Related work

In order to reduce added complexity, this library does not use the Sphinx framework with [autodoc](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html).
