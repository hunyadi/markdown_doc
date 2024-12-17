set -e

PYTHON=python3

# Run static type checker and verify formatting guidelines
$PYTHON -m mypy markdown_doc
$PYTHON -m flake8 markdown_doc
