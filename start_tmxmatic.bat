@echo off
setlocal enabledelayedexpansion

set "REPO_DIR=%~dp0"
pushd "%REPO_DIR%"

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

echo Python not found. Attempting to install via winget...
where winget >nul 2>nul
if %ERRORLEVEL%==0 (
  winget install -e --id Python.Python.3 --accept-package-agreements --accept-source-agreements --silent
) else (
  echo winget not found. Please install Python 3.10+ from https://www.python.org/downloads/windows/ then re-run this script.
  pause
  exit /b 1
)

rem Re-check after installation
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

echo Python installation did not complete. Exiting.
pause
exit /b 1

:have_python
echo Using Python: %PY_CMD%

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  %PY_CMD% -m venv .venv
  if errorlevel 1 goto venv_error
)

echo Activating virtual environment...
call ".venv\Scripts\activate.bat"
if errorlevel 1 goto venv_error

echo Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 goto pip_error

if exist "other\requirements.txt" (
  echo Installing Python dependencies...
  python -m pip install -r "other\requirements.txt"
  if errorlevel 1 goto pip_error
) else (
  echo WARNING: other\requirements.txt not found.
)

rem Ensure Flask-CORS (used by app.py) is installed
python -c "import flask_cors" 1>nul 2>nul
if errorlevel 1 (
  echo Installing Flask-CORS...
  python -m pip install flask-cors
  if errorlevel 1 goto pip_error
)

echo Starting TMXmatic...
python launcher.py
set "EXIT_CODE=%ERRORLEVEL%"

popd
exit /b %EXIT_CODE%

:venv_error
echo Failed to create/activate virtual environment.
popd
exit /b 1

:pip_error
echo Failed to install Python dependencies.
popd
exit /b 1

