@echo off
setlocal EnableDelayedExpansion
title AI Test Case Generator Agent
cd /d "%~dp0"

echo.
echo  =====================================================
echo    AI Test Case Generator Agent - Windows launcher
echo  =====================================================
echo.

rem ---- 1. Locate a compatible Python (3.10 - 3.13 preferred) -------------
set "PY="
if exist ".venv\Scripts\python.exe" goto venv_ready
for %%V in (3.13 3.12 3.11 3.10) do (
    if not defined PY (
        py -%%V -c "import sys" >nul 2>&1 && set "PY=py -%%V"
    )
)
if not defined PY (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo  [ERROR] Python 3.10 or newer was not found.
    echo          Install Python 3.13 from https://www.python.org/downloads/
    echo          and tick "Add python.exe to PATH" during installation.
    pause
    exit /b 1
)

rem ---- 2. Create the virtual environment ---------------------------------
echo  [1/4] Creating virtual environment with %PY% ...
%PY% -m venv .venv
if errorlevel 1 (
    echo  [ERROR] Could not create the virtual environment.
    pause
    exit /b 1
)

:venv_ready
set "VPY=.venv\Scripts\python.exe"

rem ---- 3. Install / update dependencies when requirements.txt changes ----
set "STAMP=.venv\.requirements.installed"
set "NEED_INSTALL=1"
if exist "%STAMP%" (
    fc /b requirements.txt "%STAMP%" >nul 2>&1 && set "NEED_INSTALL=0"
)
if "!NEED_INSTALL!"=="1" (
    echo  [2/4] Installing dependencies - first run can take a few minutes ...
    "%VPY%" -m pip install --upgrade pip --quiet --disable-pip-version-check
    "%VPY%" -m pip install -r requirements.txt --quiet --disable-pip-version-check
    if errorlevel 1 (
        echo  [ERROR] Dependency installation failed. Check your internet connection and retry.
        pause
        exit /b 1
    )
    copy /y requirements.txt "%STAMP%" >nul
) else (
    echo  [2/4] Dependencies already installed.
)

rem ---- 4. Environment file ------------------------------------------------
if not exist ".env" (
    copy /y .env.example .env >nul
    echo  [3/4] Created .env from .env.example - add GEMINI_API_KEY there if you use Gemini.
) else (
    echo  [3/4] Using existing .env configuration.
)

rem ---- 5. Pre-flight check (database + LLM provider) ----------------------
echo  [4/4] Running pre-flight checks ...
"%VPY%" setup_check.py

echo  Starting the application at http://localhost:8501  (press Ctrl+C to stop)
echo.
"%VPY%" -m streamlit run app.py --server.headless false --server.port 8501
pause
