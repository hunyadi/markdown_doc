@echo off
setlocal

set python=python.exe

%python% -m ruff check
if errorlevel 1 goto error
%python% -m ruff format --check
if errorlevel 1 goto error
%python% -m mypy markdown_doc
if errorlevel 1 goto error
%python% check.py
if errorlevel 1 goto error

goto :EOF

:error
exit /b 1
