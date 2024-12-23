@echo off
setlocal

set python=python.exe

%python% -m mypy markdown_doc || exit /b
%python% -m flake8 markdown_doc || exit /b
%python% check.py || exit /b

:quit
