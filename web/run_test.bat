@echo off
setlocal
set ROOTDIR=%~dp0
cd /d %ROOTDIR%
if not exist artifacts mkdir artifacts
set LOGFILE=artifacts\html_server.log
where python >nul 2>&1 || (
  echo Python not found
  exit /b 1
)
rem Start server
start "pyserver" cmd /c "py -3 -m http.server 8080 > %LOGFILE% 2>&1"
rem Give server some time
ping -n 3 127.0.0.1 >nul
rem Run validator
py -3 test_validator.py > %LOGFILE% 2>&1
set RES=%ERRORLEVEL%
if %RES%==0 (
  echo Validation passed
) else (
  echo Validation failed
)
exit /b %RES%
