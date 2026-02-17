@echo off
REM ============================================
REM Adaptiv Health - Quick Start Script
REM ============================================

echo.
echo ========================================
echo    Adaptiv Health Backend Startup
echo ========================================
echo.

REM Change to project directory
cd /d %~dp0

REM Check if virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo Run: python -m venv .venv
    pause
    exit /b 1
)

REM Activate virtual environment
echo [1/3] Activating virtual environment...
call .venv\Scripts\activate.bat

REM Check if packages are installed
python -c "import fastapi" 2>nul
if errorlevel 1 (
    echo [2/3] Installing dependencies...
    pip install -r requirements-minimal.txt --quiet
) else (
    echo [2/3] Dependencies already installed
)

REM Start server
echo [3/3] Starting server on http://localhost:8080
echo.
echo Press Ctrl+C to stop the server
echo.
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

pause
