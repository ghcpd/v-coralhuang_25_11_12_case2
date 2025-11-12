@echo off
setlocal enabledelayedexpansion
set ROOT=%~dp0
if exist "%ROOT%artifacts\" ( ) else ( mkdir "%ROOT%artifacts\" )
set ARTIFACTS=%ROOT%artifacts

REM Detect Python
python --version >nul 2>&1
if errorlevel 1 (
  py --version >nul 2>&1 && set PY=py || set PY=python
) else (
  set PY=python
)

start /b %PY% -m http.server 8080 > "%ARTIFACTS%\html_server.log" 2>&1
REM Give server time to start
timeout /t 1 > nul
%PY% test_validator.py > "%ARTIFACTS%\validator.log" 2>&1
set RC=%ERRORLEVEL%
REM Stop the server - best-effort
for /f "tokens=2 delims=," %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV /NH') do (
  taskkill /PID %%~i >nul 2>&1 || true
)

echo Validator exit code: %RC%
type "%ARTIFACTS%\test-report.json" || true
exit /b %RC%
