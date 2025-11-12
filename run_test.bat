@echo off
REM Test runner for Windows
REM Auto-detects OS and runs appropriate commands

echo ==========================================
echo Chat UI Test Runner (Windows)
echo ==========================================

REM Detect OS version
for /f "tokens=4-5 delims=. " %%i in ('ver') do set VERSION=%%i.%%j
echo Detected Windows Version: %VERSION%
echo.

REM Create artifacts directory
if not exist artifacts mkdir artifacts

REM Check for Python
where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set PYTHON_CMD=python
    goto :found_python
)

where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set PYTHON_CMD=py
    goto :found_python
)

echo Error: Python not found
exit /b 1

:found_python
echo Using Python: %PYTHON_CMD%
echo.

REM Check if server is already running on port 8080
netstat -an | findstr ":8080" | findstr "LISTENING" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Port 8080 already in use, attempting to use existing server...
    set SERVER_PID=
) else (
    echo Starting HTTP server on port 8080...
    start /B %PYTHON_CMD% -m http.server 8080 > artifacts\server.log 2>&1
    echo Server started in background
    timeout /t 2 /nobreak >nul
)

REM Install dependencies if needed
if not exist venv if not exist .venv (
    echo Installing dependencies...
    %PYTHON_CMD% -m pip install --user -q beautifulsoup4 html5lib playwright
    %PYTHON_CMD% -m playwright install chromium > artifacts\playwright-install.log 2>&1
)

REM Run tests
echo.
echo Running tests...
echo.

%PYTHON_CMD% test_validator.py > artifacts\test-output.log 2>&1
set TEST_EXIT_CODE=%ERRORLEVEL%

REM Stop server (find and kill python processes on port 8080)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8080" ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)

REM Print summary
echo.
echo ==========================================
echo Test execution complete
echo ==========================================
echo Logs saved to artifacts\
echo.

if %TEST_EXIT_CODE% EQU 0 (
    echo All tests passed!
    exit /b 0
) else (
    echo Some tests failed. Check artifacts\test-report.json for details.
    exit /b 1
)

