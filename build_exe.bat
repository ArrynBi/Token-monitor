@echo off
setlocal

set "ROOT=%~dp0"
set "PYTHON=C:\Users\Allen\Desktop\Coding\.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
  echo Python not found: %PYTHON%
  exit /b 1
)

pushd "%ROOT%"
"%PYTHON%" -m PyInstaller --clean --noconfirm "token-monitor.spec"
set "EXIT_CODE=%ERRORLEVEL%"
popd

if not "%EXIT_CODE%"=="0" (
  echo Build failed.
  exit /b %EXIT_CODE%
)

echo.
echo Build complete:
echo   %ROOT%dist\token-monitor.exe
exit /b 0
