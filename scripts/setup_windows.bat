@echo off
REM PrimeData Windows Setup Script
REM Quick setup script for Windows users
REM Usage: scripts\setup_windows.bat

echo ============================================================
echo PrimeData Windows Setup
echo ============================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.11+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python is installed
python --version
echo.

REM Check if Node.js is available
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not in PATH
    echo Please install Node.js 18+ from https://nodejs.org/
    pause
    exit /b 1
)

echo [OK] Node.js is installed
node --version
echo.

REM Run the Python installer
echo Running installer...
python scripts\install.py

if errorlevel 1 (
    echo.
    echo [ERROR] Installation failed
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Setup Complete!
echo ============================================================
echo.
echo Next steps:
echo 1. Edit backend\.env.local with your configuration
echo 2. Edit infra\.env.local with your configuration
echo 3. Edit ui\.env.local with your configuration
echo 4. Run: python run.py dev --services-only
echo 5. Run migrations: .venv\Scripts\python.exe -m alembic upgrade head
echo 6. Start backend: python start_backend.py
echo 7. Start frontend: cd ui ^&^& npm run dev
echo.
pause
