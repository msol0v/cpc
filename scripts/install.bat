@echo off
set "ROOT=%~dp0.."
cd /d "%ROOT%"

if not exist requirements.txt (
    echo requirements.txt is missing in the project root.
    echo Create the dependency list before installing the application.
    exit /b 1
)

if not exist .venv python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
