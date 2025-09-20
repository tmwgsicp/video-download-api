@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo   Video Download API - Windows Installer
echo ==========================================
echo.
echo This installer will:
echo 1. Check Python environment
echo 2. Create virtual environment
echo 3. Install dependencies
echo.
echo Press any key to start...
pause
cls

echo.
echo [1/4] Checking Python...
echo ========================
python --version
if errorlevel 1 (
    echo.
    echo ERROR: Python not found
    echo Please install Python 3.8+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)
echo Python check passed!

echo.
echo [2/4] Checking FFmpeg...
echo =======================
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo FFmpeg not found - this is optional
    echo For audio extraction, download from: https://ffmpeg.org
    echo Add to system PATH after installation
) else (
    echo FFmpeg found and ready!
)

echo.
echo [3/4] Creating virtual environment...
echo ====================================
if exist venv (
    echo Removing existing virtual environment...
    rmdir /s /q venv >nul 2>&1
)
python -m venv venv
if errorlevel 1 (
    echo.
    echo ERROR: Failed to create virtual environment
    echo.
    pause
    exit /b 1
)
echo Virtual environment created successfully!

echo.
echo [4/4] Installing dependencies...
echo ===============================
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

echo Updating pip...
python -m pip install --upgrade pip --quiet

echo Installing dependencies (this may take several minutes)...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo Installation failed, trying China mirror...
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/ --quiet
    if errorlevel 1 (
        echo Installing packages individually...
        pip install fastapi uvicorn python-multipart yt-dlp pydantic pyyaml requests psutil --quiet
        if errorlevel 1 (
            echo ERROR: Installation failed
            pause
            exit /b 1
        )
    )
)

echo.
echo Final setup...
if not exist temp mkdir temp
if not exist logs mkdir logs

echo Testing imports...
python -c "import fastapi, uvicorn, yt_dlp; print('Core imports successful!')"

echo.
echo ==========================================
echo Installation Complete!
echo ==========================================
echo.
echo To start the API:
echo   Double-click: run.bat
echo.
echo API will be available at:
echo   http://localhost:8000
echo.
echo For FFmpeg (audio extraction):
echo   Download from: https://ffmpeg.org
echo   Add to system PATH
echo.
pause
