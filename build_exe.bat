@echo off
setlocal

set "ROOT=%~dp0"
call "%ROOT%build_win.bat"
if errorlevel 1 (
  exit /b %ERRORLEVEL%
)
