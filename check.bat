@echo off
setlocal

set python=python.exe

%python% -m mypy markdown_doc || exit /b 1
%python% -m flake8 markdown_doc || exit /b 2
%python% check.py || exit /b 3

:quit
