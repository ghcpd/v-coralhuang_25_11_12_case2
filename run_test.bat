@echo off
REM Chat UI Test Runner for Windows
REM Auto-detects OS and starts local server, runs validation, and generates report

setlocal enabledelayedexpansion

REM Verify we're on Windows
if not defined OS (
    echo [ERROR] OS environment variable not found. Are you on Windows?
    exit /b 1
)
echo [OS] Windows detected: %OS%

REM Create artifacts directory
if not exist artifacts mkdir artifacts

REM Write start timestamp
for /f %%A in ('powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ'"') do (
    set START_TIME=%%A
)
echo Start time: %START_TIME% > artifacts\agent_runtime.txt

REM Detect Python executable
set PYTHON_CMD=
if exist "py.exe" (
    set PYTHON_CMD=py
) else (
    for /f %%A in ('where python 2^>nul') do (
        set PYTHON_CMD=python
        goto python_found
    )
)

:python_found
if not defined PYTHON_CMD (
    echo [ERROR] Python not found. Please install Python 3.
    exit /b 1
)

echo [Python] Using: %PYTHON_CMD%
%PYTHON_CMD% --version

REM Install requirements
echo [Setup] Installing dependencies...
%PYTHON_CMD% -m pip install -q -r requirements.txt 2>nul || (
    echo [Setup] pip install had issues, but continuing...
)

REM Start HTTP server in background
echo [Server] Starting HTTP server on port 8080...
set PORT=8080

REM Try py -m http.server first, fall back to python -m http.server
%PYTHON_CMD% -m http.server %PORT% > nul 2>&1 &
set SERVER_PID=%ERRORLEVEL%

echo [Server] HTTP server started (PID check via port)

REM Wait for server to be ready
echo [Server] Waiting for server to be reachable on http://localhost:%PORT%...
set MAX_WAIT=30
set ELAPSED=0

:wait_loop
if %ELAPSED% geq %MAX_WAIT% (
    echo [ERROR] Server did not become reachable after %MAX_WAIT% seconds
    taskkill /F /FI "WINDOWTITLE eq *http.server*" >nul 2>&1
    exit /b 1
)

timeout /t 1 /nobreak >nul 2>&1
powershell -NoProfile -Command "try { $resp = Invoke-WebRequest -Uri 'http://localhost:%PORT%/ui_fixed.html' -UseBasicParsing -ErrorAction Stop; exit 0 } catch { exit 1 }" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [Server] ✓ Server is ready
    goto server_ready
)

set /a ELAPSED=%ELAPSED%+1
goto wait_loop

:server_ready
REM Run validator
echo [Validator] Running test_validator.py...
%PYTHON_CMD% test_validator.py
set TEST_RESULT=%ERRORLEVEL%

if %TEST_RESULT% equ 0 (
    echo [Validator] ✓ All validations passed
) else (
    echo [Validator] ✗ Validations failed
)

REM Write end timestamp
for /f %%A in ('powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ'"') do (
    set END_TIME=%%A
)
echo End time: %END_TIME% >> artifacts\agent_runtime.txt

REM Kill server
taskkill /F /FI "WINDOWTITLE eq *http.server*" >nul 2>&1 || taskkill /F /IM python.exe >nul 2>&1 || true
timeout /t 1 /nobreak >nul 2>&1
echo [Server] Stopped

REM Exit with test result
exit /b %TEST_RESULT%
