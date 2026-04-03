@echo off
title Thermal Sentinel — Running
echo.
echo  ============================================
echo   Starting Thermal Sentinel...
echo  ============================================
echo.

echo  [1/3] Starting API server...
start "Thermal Sentinel — API" cmd /k "cd src && uvicorn main:app --host 0.0.0.0 --port 8000"

echo  Waiting for API to start...
timeout /t 4 /nobreak >nul

echo  [2/3] Starting thermal scanner...
start "Thermal Sentinel — Detector" cmd /k "python src/detector.py"

echo  Waiting for detector...
timeout /t 3 /nobreak >nul

echo  [3/3] Starting dashboard server...
start "Thermal Sentinel — Dashboard" cmd /k "python -m http.server 3000"

timeout /t 2 /nobreak >nul

echo.
echo  Opening dashboard in browser...
start http://localhost:3000/dashboard.html

echo.
echo  ============================================
echo   All services running!
echo   Dashboard: http://localhost:3000/dashboard.html
echo   API docs:  http://localhost:8000/docs
echo  ============================================
echo.
echo  To stop: close all 3 black terminal windows
echo.
pause
