@echo off
setlocal

set PYTHON_310="C:\Program Files\Python310\python.exe"
set PYTHON_311="C:\Program Files\Python311\python.exe"
set PYTHON_312="C:\Program Files\Python312\python.exe"
set PYTHON_313="C:\Program Files\Python313\python.exe"
set PYTHON_314="C:\Program Files\Python314\python.exe"

rem Run static type checker and verify formatting guidelines
%PYTHON_314% -m ruff check
if errorlevel 1 goto error
%PYTHON_314% -m ruff format --check
if errorlevel 1 goto error
%PYTHON_314% -m mypy markdown_doc
if errorlevel 1 goto error

rem Run unit tests
if exist %PYTHON_310% %PYTHON_310% check.py
if errorlevel 1 goto error
if exist %PYTHON_311% %PYTHON_311% check.py
if errorlevel 1 goto error
if exist %PYTHON_312% %PYTHON_312% check.py
if errorlevel 1 goto error
if exist %PYTHON_313% %PYTHON_313% check.py
if errorlevel 1 goto error
if exist %PYTHON_314% %PYTHON_314% check.py
if errorlevel 1 goto error

goto EOF

:error
exit /b %errorlevel%

:EOF
