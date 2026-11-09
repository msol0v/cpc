@echo off
set "ROOT=%~dp0.."
cd /d "%ROOT%"

if not exist .venv\Scripts\python.exe (
    echo Virtual environment not found. Run scripts\install.bat first.
    exit /b 1
)

.venv\Scripts\python.exe main.py
