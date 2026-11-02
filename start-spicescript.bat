@echo off
rem Starts SpiceScript (backend + frontend) from the folder this file sits in, then opens the app.
rem Keep both black windows open while you use the app. Close them to stop the servers.
set ROOT=%~dp0
set PY=C:\Users\falak\AppData\Local\Programs\Python\Python315\python.exe
if not exist %PY% set PY=python
start "SpiceScript backend" cmd /k "cd /d %ROOT%backend && %PY% -m uvicorn app.main:app --reload"
start "SpiceScript frontend" cmd /k "cd /d %ROOT%frontend && npm install && npm run dev"
echo Starting both servers. The app opens in about 20 seconds.
timeout /t 20 /nobreak >nul
start http://localhost:5173
