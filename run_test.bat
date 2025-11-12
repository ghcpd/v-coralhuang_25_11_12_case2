@echo off
REM Chat UI Test Runner - Windows
REM Auto-detects OS and runs complete validation suite

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set PORT=8080
set LOG_DIR=%SCRIPT_DIR%artifacts
set SERVER_LOG=%LOG_DIR%\server.log
set TEST_REPORT=%LOG_DIR%\test-report.json

REM Create artifacts directory
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo ================================
echo Chat UI Validator - Test Suite
echo ================================
echo OS: Windows
echo Script directory: %SCRIPT_DIR%
echo.

REM Step 1: Check dependencies
echo [1/4] Checking dependencies...

python --version >nul 2>&1
if errorlevel 1 (
    py --version >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Python not found. Please install Python 3.8+
        exit /b 1
    )
    set PYTHON=py
) else (
    set PYTHON=python
)

for /f "tokens=2" %%i in ('%PYTHON% --version 2^>^&1') do set PYTHON_VERSION=%%i
echo   - Python %PYTHON_VERSION% found

REM Step 2: Install requirements
echo [2/4] Installing Python dependencies...

if not exist "%SCRIPT_DIR%.venv" (
    %PYTHON% -m venv "%SCRIPT_DIR%.venv"
)

call "%SCRIPT_DIR%.venv\Scripts\activate.bat"
%PYTHON% -m pip install -q -r "%SCRIPT_DIR%requirements.txt"
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    exit /b 1
)
echo   - Dependencies installed

REM Step 3: Start HTTP server
echo [3/4] Starting HTTP server on port %PORT%...

REM Kill any existing server on this port
for /f "tokens=5" %%a in ('netstat -aon ^| find ":%PORT%" ^| find "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1 || true
)

timeout /t 1 /nobreak >nul

REM Start new server in background
cd /d "%SCRIPT_DIR%"
start "Chat Server" /B %PYTHON% -m http.server %PORT%

REM Wait for server to start
timeout /t 2 /nobreak >nul

REM Check if server started
netstat -aon | find ":%PORT%" | find "LISTENING" >nul
if errorlevel 1 (
    echo ERROR: Failed to start HTTP server
    echo Check %SERVER_LOG% for details
    exit /b 1
)

echo   - Server started on port %PORT%

REM Step 4: Run tests
echo [4/4] Running validation tests...
echo.

%PYTHON% "%SCRIPT_DIR%test_validator.py"
set TEST_EXIT_CODE=!ERRORLEVEL!

REM Print results
echo.
echo ================================
if exist "%TEST_REPORT%" (
    echo Test Report: %TEST_REPORT%
)

if !TEST_EXIT_CODE! equ 0 (
    echo - ALL TESTS PASSED
) else (
    echo - SOME TESTS FAILED
)

REM Try to stop servers gracefully
taskkill /F /IM python.exe >nul 2>&1 || true
timeout /t 1 /nobreak >nul

exit /b !TEST_EXIT_CODE!
