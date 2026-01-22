@echo off
setlocal enabledelayedexpansion

set "PROJECT_DIR=%~dp0"
pushd "%PROJECT_DIR%"

echo ========================================
echo LLM Quality Module - Virtual Environment Setup
echo ========================================
echo.

echo Checking for Python...
set "PY_CMD="

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  set "PY_CMD=py -3"
  goto have_python
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
  set "PY_CMD=python"
  goto have_python
)

echo ERROR: Python not found!
echo Please install Python 3.8+ from https://www.python.org/downloads/
pause
exit /b 1

:have_python
echo Using Python: %PY_CMD%
echo.

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  %PY_CMD% -m venv .venv
  if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
  )
  echo Virtual environment created successfully.
) else (
  echo Virtual environment already exists.
)
echo.

echo Activating virtual environment...
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
  echo ERROR: Failed to activate virtual environment
  pause
  exit /b 1
)
echo.

echo Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 (
  echo ERROR: Failed to upgrade pip
  pause
  exit /b 1
)
echo.

if exist "requirements.txt" (
  echo Installing Python dependencies...
  python -m pip install -r "requirements.txt"
  if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    echo.
    echo NOTE: Some dependencies (like torch with CUDA) may require
    echo additional setup. See documentation for details.
    pause
    exit /b 1
  )
  echo Dependencies installed successfully.
) else (
  echo WARNING: requirements.txt not found.
)

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo To activate the virtual environment in the future, run:
echo   .venv\Scripts\activate.bat
echo.
echo To run tests:
echo   pytest
echo.
pause
