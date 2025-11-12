@echo off
REM Test runner for Windows
REM Detects OS and runs validation tests

setlocal enabledelayedexpansion

set START_TIME=%time%
set START_TIMESTAMP=%date% %time%

echo ==========================================
echo Chat UI Test Runner (Windows)
echo Start time: %START_TIMESTAMP%
echo ==========================================

REM Detect OS
if "%OS%"=="Windows_NT" (
    echo Detected OS: Windows
) else (
    echo Detected OS: Unknown
)

REM Create artifacts directory
if not exist "artifacts" mkdir artifacts
if not exist "artifacts\screenshots" mkdir artifacts\screenshots

REM Find Python command
where py >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
) else (
    where python >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_CMD=python
    ) else (
        echo ERROR: Python not found. Please install Python 3.
        exit /b 1
    )
)

echo Using Python: %PYTHON_CMD%

REM Check if Playwright is installed
echo Checking Playwright installation...
%PYTHON_CMD% -c "import playwright" 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Playwright not installed. Run: pip install -r requirements.txt ^&^& playwright install chromium
    exit /b 1
)

REM Start HTTP server in background
echo Starting HTTP server on port 8080...
start /b %PYTHON_CMD% -m http.server 8080 > artifacts\server.log 2>&1

REM Wait for server to be ready
echo Waiting for server to be ready...
set MAX_RETRIES=30
set RETRY_COUNT=0

:wait_loop
set /a RETRY_COUNT+=1
if %RETRY_COUNT% gtr %MAX_RETRIES% (
    echo ERROR: Server failed to start after %MAX_RETRIES% seconds
    exit /b 1
)

REM Try to connect (Windows doesn't have curl by default, use PowerShell)
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:8080/ui_fixed.html' -TimeoutSec 1 -UseBasicParsing; exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel% equ 0 (
    echo Server is ready!
    goto server_ready
)

timeout /t 1 /nobreak >nul
goto wait_loop

:server_ready

REM Run validator
echo.
echo Running test validator...
%PYTHON_CMD% test_validator.py
set VALIDATOR_EXIT=%errorlevel%

REM Record end time
set END_TIME=%time%
set END_TIMESTAMP=%date% %time%

REM Write runtime info
(
    echo Start: %START_TIMESTAMP%
    echo End: %END_TIMESTAMP%
    echo OS: Windows
    echo Python: %PYTHON_CMD%
    echo Exit Code: %VALIDATOR_EXIT%
) > artifacts\agent_runtime.txt

REM Print final summary
echo.
echo ==========================================
echo Test Run Complete
echo Exit Code: %VALIDATOR_EXIT%
echo ==========================================

REM Find and kill the server process
for /f "tokens=2" %%i in ('netstat -ano ^| findstr :8080 ^| findstr LISTENING') do (
    taskkill /PID %%i /F >nul 2>&1
)

exit /b %VALIDATOR_EXIT%

