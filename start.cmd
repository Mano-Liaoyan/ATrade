@echo off
setlocal

set "COMMAND=%~1"
if "%COMMAND%"=="" goto :usage

if "%COMMAND%"=="run" goto :run

>&2 echo Unsupported command: %COMMAND%
goto :usage

:run
powershell -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
exit /b %ERRORLEVEL%

:usage
>&2 echo Usage: ./start.cmd run
exit /b 1
