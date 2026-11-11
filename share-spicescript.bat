@echo off
rem Run this after start-spicescript.bat to create a temporary public link.
where.exe cloudflared >nul 2>nul
if errorlevel 1 (
    echo Cloudflare Tunnel is not installed.
    echo Install cloudflared from https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
    exit /b 1
)

echo Starting a temporary public tunnel to SpiceScript on http://localhost:5173.
echo Share the https:// URL printed below. Keep this window and both app servers open.
echo Anyone with the link can reach the app; close this window to stop sharing.
cloudflared tunnel --url http://localhost:5173
