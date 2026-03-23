@echo off
setlocal

set "ROOT=%~dp0"
set "PYTHON=%ROOT%.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=C:\Users\Allen\Desktop\Coding\.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
  echo Python not found: %PYTHON%
  exit /b 1
)

pushd "%ROOT%"
"%PYTHON%" "tools\generate_windows_icon.py"
if errorlevel 1 (
  popd
  echo Icon generation failed.
  exit /b 1
)

"%PYTHON%" -m PyInstaller --clean --noconfirm "token-monitor.win.spec"
set "EXIT_CODE=%ERRORLEVEL%"
if exist "dist\token-monitor.exe" del /q "dist\token-monitor.exe"

set "DIST_EXE="
for %%I in ("dist\*.exe") do set "DIST_EXE=%%~fI"
popd

if not "%EXIT_CODE%"=="0" (
  echo Build failed.
  exit /b %EXIT_CODE%
)

if not defined DIST_EXE (
  echo Built EXE not found.
  exit /b 1
)

if not exist "%DIST_EXE%" (
  echo Built EXE not found: %DIST_EXE%
  exit /b 1
)

set "RELEASE_DIR=%ROOT%release\win"
set "ZIP_FILE=%ROOT%release\token-monitor-win.zip"
if not exist "%RELEASE_DIR%" mkdir "%RELEASE_DIR%"
copy /Y "%DIST_EXE%" "%RELEASE_DIR%\" >nul
if exist "%ROOT%config.example.json" copy /Y "%ROOT%config.example.json" "%RELEASE_DIR%\config.example.json" >nul
if exist "%ZIP_FILE%" del /q "%ZIP_FILE%"

"%PYTHON%" "tools\package_release.py" --output "%ZIP_FILE%" --root-name "token-monitor-win" "%DIST_EXE%" "%ROOT%config.example.json"
if errorlevel 1 (
  echo ZIP packaging failed.
  exit /b 1
)

echo.
echo Windows build complete:
echo   %DIST_EXE%
echo Release package updated:
echo   %RELEASE_DIR%
echo ZIP package:
echo   %ZIP_FILE%
exit /b 0
