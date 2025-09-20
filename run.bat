@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo   Video Download API - Start Service
echo ==========================================
echo.

if not exist venv (
    echo ERROR: API not installed
    echo Please run install.bat first
    echo.
    pause
    exit /b 1
)

if not exist start.py (
    echo ERROR: start.py not found
    echo Make sure you're in the correct directory
    echo.
    pause
    exit /b 1
)

echo Starting API service...
echo.
echo Current directory: %CD%
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Starting service...
echo.
echo Service will be available at:
echo   Main API: http://localhost:8000
echo   Documentation: http://localhost:8000/docs
echo   Health Check: http://localhost:8000/api/health
echo.
echo Press Ctrl+C to stop the service
echo ==========================================
echo.

python start.py

echo.
echo ==========================================
echo Service stopped
echo ==========================================
echo.
pause
