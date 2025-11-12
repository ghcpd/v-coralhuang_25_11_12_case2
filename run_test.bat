@echo off
REM One-click test runner (Windows)
setlocal
set ART_DIR=artifacts
if not exist %ART_DIR% mkdir %ART_DIR%
set PY=py
where %PY% >nul 2>&1 || set PY=python
set PORT=8080
REM Ensure runtime packages are installed
%PY% -m pip install -r requirements.txt --quiet || echo 'pip install failed (they may already be present)'
REM For playwright, ensure the browsers are installed
%PY% -m playwright install >/dev/null 2>&1 || echo 'playwright install failed (maybe already installed)'
REM Start server
start /b %PY% -m http.server %PORT% >nul 2>&1
REM wait for server
echo Waiting for http://localhost:%PORT% ...
set tries=0
:waitloop
  %PY% -c "import urllib.request,sys; urllib.request.urlopen('http://localhost:%PORT%/ui_fixed.html').read()" >nul 2>&1
  if %errorlevel%==0 goto server_ready
  timeout /t 1 >nul
  set /a tries+=1
  if %tries% GTR 30 goto fail
  goto waitloop
:server_ready
  echo Server ready
REM Run validator
%PY% test_validator.py
if %errorlevel%==0 (
  echo PASS
  set rc=0
) else (
  echo FAIL
  set rc=1
)
REM write runtime
for /f "tokens=2" %%t in ('powershell -Command "[int](Get-Date -UFormat %s)"') do set END=%%t
for /f "tokens=2" %%t in ('powershell -Command "[int](Get-Date -UFormat %s) - %END%"') do set DURATION=%%t
echo {"end":%END%,"duration":%DURATION%} > "%ART_DIR%\agent_runtime.txt"
exit /b %rc%
:fail
  echo Server not responding after timeout
  exit /b 1
