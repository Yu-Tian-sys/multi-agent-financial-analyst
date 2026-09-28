@echo off
title Multi-Agent Financial Analyst - Launcher

echo ============================================
echo    Multi-Agent Financial Analyst - Launcher
echo ============================================
echo.

echo [1/2] Starting backend...
start "Backend" cmd /k "cd /d %~dp0 && python -m uvicorn src.main:app --host 127.0.0.1 --port 8000"

timeout /t 3 /nobreak >nul

echo [2/2] Starting frontend...
start "Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo Waiting for frontend to be ready...
timeout /t 6 /nobreak >nul

echo Opening browser...
start http://localhost:5173/

echo.
echo ============================================
echo   Done!
echo.
echo   - Backend window: "Backend"
echo   - Frontend window: "Frontend"
echo   - Browser: http://localhost:5173/
echo.
echo   Close those two windows to stop services.
echo ============================================
echo.
pause
