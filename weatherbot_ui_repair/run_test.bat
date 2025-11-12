@echo off
setlocal enabledelayedexpansion
cd /d %~dp0
REM Start HTTP server using py or python
where py >nul 2>&1
if %errorlevel%==0 (
  set PY=py
) else (
  set PY=python
)
%PY% -m http.server 8080 >nul 2>&1 &
REM Wait for server
for /L %%i in (1,1,10) do (
  curl -s --head http://localhost:8080 | findstr /C:"200 OK" >nul 2>&1 && goto server_ready
  timeout /t 1 >nul
)
:server_ready
echo Server started on port 8080
set START=%time%
echo Running validator...
%PY% test_validator.py
set STATUS=%ERRORLEVEL%
echo start:%START%>artifacts\agent_runtime.txt
echo end:%time%>>artifacts\agent_runtime.txt
exit /b %STATUS%