@echo off
rem Starts SpiceScript (backend + frontend) from the folder this file sits in, then opens the app.
rem Keep both black windows open while you use the app. Close them to stop the servers.
cd /d "%~dp0"
set "PYTHON=python"
if exist ".venv\Scripts\python.exe" set "PYTHON=..\.venv\Scripts\python.exe"
start "SpiceScript backend" cmd /k "cd /d backend && %PYTHON% -m uvicorn app.main:app --reload"
start "SpiceScript frontend" cmd /k "cd /d frontend && npm install && npm run dev"
echo Starting both servers. The app opens in about 20 seconds.
timeout /t 20 /nobreak >nul
start http://localhost:5173
