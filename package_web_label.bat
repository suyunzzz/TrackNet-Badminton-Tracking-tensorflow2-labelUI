@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "VENV_DIR=%SCRIPT_DIR%.build-venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
  echo [1/4] Creating build virtual environment...
  where py >nul 2>nul
  if %errorlevel%==0 (
    py -3 -m venv "%VENV_DIR%"
  ) else (
    python -m venv "%VENV_DIR%"
  )
)

echo [2/4] Installing build dependencies...
"%PYTHON_EXE%" -m pip install --upgrade pip
if errorlevel 1 exit /b 1
"%PYTHON_EXE%" -m pip install -r requirements.txt pyinstaller
if errorlevel 1 exit /b 1

echo [3/4] Building standalone app...
"%PYTHON_EXE%" -m PyInstaller --clean web_label.spec
if errorlevel 1 exit /b 1

echo [4/4] Build complete.
echo Executable output:
echo   %SCRIPT_DIR%dist\web_label.exe
