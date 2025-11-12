@echo off
set ROOT=%~dp0
set ART=%ROOT%artifacts
if not exist "%ART%" mkdir "%ART%"

where python >nul 2>&1
if %errorlevel% NEQ 0 (
  where py >nul 2>&1
  if %errorlevel% NEQ 0 (
    echo python not found. Please install python.
    exit /b 2
  ) else (
    set PY=py
  )
) else (
  set PY=python
)

REM start server
start /B %PY% -m http.server 8080 > "%ART%\html_server.log" 2>&1
ping -n 2 127.0.0.1 >nul

REM run tests
%PY% "%ROOT%test_validator.py"
exit /b %ERRORLEVEL%
