@echo off
setlocal
set ROOT=%~dp0
cd /d %ROOT%

set START_TS=%DATE% %TIME%
if defined VIRTUAL_ENV (
  echo Using venv
)

:: Resolve python executable
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  set PY=py
) else (
  where python >nul 2>nul
  if %ERRORLEVEL%==0 (
    set PY=python
  ) else (
    echo Python not found
    exit /b 1
  )
)

:: Install requirements
%PY% -m pip install -r requirements.txt --upgrade >nul 2>nul
%PY% -m playwright install >nul 2>nul || true

:: Start server via PowerShell and capture PID
for /f "tokens=*" %%P in ('powershell -Command "(Start-Process -FilePath %PY% -ArgumentList '-m http.server 8080' -PassThru).Id"') do set SERVER_PID=%%P

echo Server PID: %SERVER_PID%

:: Wait until server is reachable
powershell -Command "for($i=0;$i -lt 20;$i++){try{(Invoke-WebRequest -Uri 'http://localhost:8080/ui_fixed.html' -TimeoutSec 2 -UseBasicParsing) | Out-Null; exit 0;}catch{Start-Sleep -Milliseconds 250}}; exit 1"
if %ERRORLEVEL% NEQ 0 (
  echo Server did not start
  taskkill /PID %SERVER_PID% /F >nul 2>nul || true
  exit /b 1
)

:: Run validator
%PY% test_validator.py
set STATUS=%ERRORLEVEL%

:: Save timestamps
set END_TS=%DATE% %TIME%
(echo start_ts=%START_TS%)>artifacts\run_test_env.txt
(echo end_ts=%END_TS%)>>artifacts\run_test_env.txt

:: Kill server
taskkill /PID %SERVER_PID% /F >nul 2>nul || true

exit /b %STATUS%
