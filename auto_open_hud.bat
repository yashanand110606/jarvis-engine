@echo off
cd C:\Users\Yash
echo [SYSTEM] Starting J.A.R.V.I.S. Production...

:: 1. Start HUD server (serves HTML + API on same origin)
start /min "" python jarvis_hud_server.py

:: 2. Wait for server to boot
timeout /t 3 /nobreak >nul

:: 3. Open HUD in Chrome (from server, not file://)
start "" chrome --kiosk "http://localhost:8001/"

:: 4. Start JARVIS
echo [SYSTEM] Launching Vocal Module...
python jarvis.py
pause
