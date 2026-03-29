@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "VENV_DIR=%SCRIPT_DIR%venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
  echo [1/3] Creating local virtual environment...
  where py >nul 2>nul
  if %errorlevel%==0 (
    py -3 -m venv "%VENV_DIR%"
  ) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
      python -m venv "%VENV_DIR%"
    ) else (
      echo Python 3 was not found.
      echo Install Python 3 first, then run this launcher again.
      pause
      exit /b 1
    )
  )
)

if not exist "%PYTHON_EXE%" (
  echo Failed to create the virtual environment at:
  echo %VENV_DIR%
  pause
  exit /b 1
)

echo [2/3] Installing or updating launcher dependencies...
"%PYTHON_EXE%" -m pip install --upgrade pip
if errorlevel 1 (
  echo Failed to upgrade pip.
  pause
  exit /b 1
)

"%PYTHON_EXE%" -m pip install -r requirements.txt
if errorlevel 1 (
  echo Failed to install required packages.
  pause
  exit /b 1
)

echo [3/3] Starting web label tool...
if "%~1"=="" (
  "%PYTHON_EXE%" web_label.py
) else (
  "%PYTHON_EXE%" web_label.py --label_video_path "%~1"
)

if errorlevel 1 (
  echo The web label tool exited with an error.
  pause
  exit /b 1
)
