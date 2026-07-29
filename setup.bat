@echo off
REM ═══════════════════════════════════════════════════════════════
REM  ONE-CLICK SETUP: Documentation AI Tool
REM ═══════════════════════════════════════════════════════════════
REM
REM  This script sets up everything needed to run the app:
REM    1. Installs Ollama (local AI engine)
REM    2. Pulls the AI model for offline use
REM    3. Installs Python dependencies
REM    4. Installs Node.js dependencies
REM
REM  After this completes, run: npm start
REM
REM  Prerequisites:
REM    - Python 3.10+ (with pip)
REM    - Node.js 18+ (with npm)
REM    - Internet connection (first time only)
REM
REM ═══════════════════════════════════════════════════════════════

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║  Documentation AI Tool - Setup                           ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

REM ─── Step 1: Check prerequisites ───────────────────────────
echo [1/5] Checking prerequisites...

where py >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    where python >nul 2>nul
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Python not found. Install Python 3.10+ from https://python.org
        exit /b 1
    )
)
echo       Python: OK

where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Node.js not found. Install Node.js 18+ from https://nodejs.org
    exit /b 1
)
echo       Node.js: OK
echo.

REM ─── Step 2: Install Ollama ─────────────────────────────────
echo [2/5] Setting up Ollama (local AI engine)...

where ollama >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo       Ollama not found. Downloading installer...

    REM Download Ollama Windows installer
    powershell -Command "& { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://ollama.com/download/OllamaSetup.exe' -OutFile '%TEMP%\OllamaSetup.exe' }"

    if not exist "%TEMP%\OllamaSetup.exe" (
        echo ERROR: Failed to download Ollama. Check your internet connection.
        echo You can manually install from: https://ollama.com/download
        exit /b 1
    )

    echo       Installing Ollama (this may take a minute)...
    start /wait "" "%TEMP%\OllamaSetup.exe" /VERYSILENT /NORESTART
    del "%TEMP%\OllamaSetup.exe" >nul 2>nul

    REM Refresh PATH
    set "PATH=%LOCALAPPDATA%\Programs\Ollama;%PATH%"

    where ollama >nul 2>nul
    if %ERRORLEVEL% NEQ 0 (
        echo       Ollama installed but not in PATH yet.
        echo       Please restart this terminal and run setup.bat again.
        exit /b 1
    )
) else (
    echo       Ollama: Already installed
)
echo.

REM ─── Step 3: Start Ollama and pull model ────────────────────
echo [3/5] Pulling AI model (llama3.2 - ~2GB download, first time only)...

REM Ensure Ollama is running
tasklist /fi "imagename eq ollama.exe" 2>nul | find /i "ollama.exe" >nul
if %ERRORLEVEL% NEQ 0 (
    echo       Starting Ollama service...
    start /b "" ollama serve >nul 2>nul
    timeout /t 3 /nobreak >nul
)

REM Pull the model (skips if already downloaded)
ollama pull llama3.2:latest
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to pull AI model. Ensure Ollama is running and you have internet.
    exit /b 1
)
echo       Model ready for offline use.
echo.

REM ─── Step 4: Install Python dependencies ───────────────────
echo [4/5] Installing Python dependencies...
pip install "markitdown[all]" openai --quiet
if %ERRORLEVEL% NEQ 0 (
    py -m pip install "markitdown[all]" openai --quiet
)
echo       Done.
echo.

REM ─── Step 5: Install Node.js dependencies ──────────────────
echo [5/5] Installing Node.js dependencies...
call npm install --quiet
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: npm install failed.
    exit /b 1
)
echo       Done.
echo.

echo ╔══════════════════════════════════════════════════════════╗
echo ║  SETUP COMPLETE                                          ║
echo ╠══════════════════════════════════════════════════════════╣
echo ║                                                          ║
echo ║  To run the app:                                         ║
echo ║    npm start                                             ║
echo ║                                                          ║
echo ║  To run in dev mode (with DevTools):                     ║
echo ║    npm run dev                                           ║
echo ║                                                          ║
echo ║  The AI Assistant works fully offline after this setup.  ║
echo ║  Ollama runs in the background automatically.            ║
echo ║                                                          ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
pause
