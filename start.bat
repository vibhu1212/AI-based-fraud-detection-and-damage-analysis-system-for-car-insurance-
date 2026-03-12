@echo off
REM ============================================================
REM InsurAI — Start All Services (Windows)
REM Double-click this file or run: start.bat
REM ============================================================

title InsurAI - Module Testing Dashboard
color 0B

echo.
echo   === InsurAI — AI Insurance Survey Agent ===
echo   Module Testing Dashboard
echo   ==========================================
echo.

set "PROJECT_DIR=%~dp0"

REM ── Check prerequisites ──────────────────────────────────
echo [*] Checking prerequisites...

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [X] Python is not installed. Please install Python 3.10+ first.
    pause
    exit /b 1
)

where node >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [X] Node.js is not installed. Please install Node.js 18+ first.
    pause
    exit /b 1
)

where npm >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [X] npm is not found. Please install Node.js 18+ first.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo   [OK] Python %%v
for /f "tokens=1" %%v in ('node --version 2^>^&1') do echo   [OK] Node.js %%v
echo.

REM ── Backend setup ─────────────────────────────────────────
echo [*] Setting up backend...

set "BACKEND_DIR=%PROJECT_DIR%backend"
set "VENV_DIR=%BACKEND_DIR%\venv"

REM Create virtual environment if it doesn't exist
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo   Creating Python virtual environment...
    python -m venv "%VENV_DIR%"
)

REM Activate virtual environment
call "%VENV_DIR%\Scripts\activate.bat"

REM Install dependencies if needed
if not exist "%VENV_DIR%\.deps_installed" (
    echo   Installing Python dependencies...
    pip install -r "%BACKEND_DIR%\requirements.txt" --quiet
    echo. > "%VENV_DIR%\.deps_installed"
) else (
    echo   [OK] Python dependencies already installed
)

REM Create .env if it doesn't exist
if not exist "%BACKEND_DIR%\.env" (
    if exist "%BACKEND_DIR%\.env.example" (
        copy "%BACKEND_DIR%\.env.example" "%BACKEND_DIR%\.env" >nul
        echo   [OK] Created .env from .env.example
    )
)

echo   [OK] Backend ready
echo.

REM ── Frontend setup ────────────────────────────────────────
echo [*] Setting up frontend...

set "FRONTEND_DIR=%PROJECT_DIR%frontend"

REM Install dependencies if needed
if not exist "%FRONTEND_DIR%\node_modules" (
    echo   Installing Node.js dependencies...
    cd /d "%FRONTEND_DIR%"
    npm install --silent
    cd /d "%PROJECT_DIR%"
) else (
    echo   [OK] Node.js dependencies already installed
)

echo   [OK] Frontend ready
echo.

REM ── Start services ────────────────────────────────────────
echo [*] Starting services...
echo.

REM Start backend in a new window
echo   Starting backend on http://localhost:8000 ...
start "InsurAI Backend" cmd /c "cd /d "%BACKEND_DIR%" && call "%VENV_DIR%\Scripts\activate.bat" && uvicorn app.main:app --reload --port 8000 --host 0.0.0.0"

REM Wait for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend in a new window
echo   Starting frontend on http://localhost:5173 ...
start "InsurAI Frontend" cmd /c "cd /d "%FRONTEND_DIR%" && npm run dev -- --host 0.0.0.0 --port 5173"

timeout /t 3 /nobreak >nul

echo.
echo   ================================================
echo   [OK] InsurAI is running!
echo.
echo   Frontend:  http://localhost:5173
echo   Backend:   http://localhost:8000
echo   API Docs:  http://localhost:8000/api/docs
echo.
echo   Close the terminal windows to stop services.
echo   ================================================
echo.

REM Open browser
start http://localhost:5173

pause
