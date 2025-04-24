set -e

PYTHON_EXECUTABLE=${PYTHON:-python3}

# Run static type checker and verify formatting guidelines
$PYTHON_EXECUTABLE -m mypy markdown_doc
$PYTHON_EXECUTABLE -m flake8 markdown_doc

# Run unit tests
$PYTHON_EXECUTABLE check.py
