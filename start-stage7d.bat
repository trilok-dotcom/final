@echo off
echo ===================================================
echo   RESQROUTE AI - STAGE 7D REAL-TIME GPS LAUNCHER
echo ===================================================
echo PC Wi-Fi IP: 192.168.1.5
echo.
echo Starting FastAPI Backend on http://0.0.0.0:8000 ...
start "RESQROUTE Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

echo Starting React Frontend on http://0.0.0.0:5173 ...
start "RESQROUTE Frontend" cmd /k "cd /d %~dp0 && npm run dev"

echo.
echo Launching Cloudflare HTTPS Tunnel (No Password / No Blank Screen) ...
start "RESQROUTE Cloudflare Tunnel" cmd /k "cd /d %~dp0 && .\cloudflared.exe tunnel --url http://localhost:5173"

echo.
echo Launcher complete. Keep all 3 terminal windows open while testing on your Android phone!
pause
