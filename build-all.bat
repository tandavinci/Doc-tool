@echo off
REM ═══════════════════════════════════════════════════════════════
REM  ONE-STEP BUILD: Documentation AI Tool (Offline Package)
REM ═══════════════════════════════════════════════════════════════
REM
REM  This script builds the complete standalone application:
REM    1. Bundles Python backend into backend.exe
REM    2. Bundles Ollama + AI model for offline use
REM    3. Packages everything into an installable Windows app
REM
REM  Prerequisites (build machine only):
REM    - Python 3.10+ with pip
REM    - Node.js 18+ with npm
REM    - Ollama installed with llama3.2 model pulled
REM      (run setup.bat first if not done)
REM
REM  The output is a standalone installer that works on any
REM  Windows machine WITHOUT Python, Node.js, or internet.
REM ═══════════════════════════════════════════════════════════════

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║  Building Documentation AI Tool - Offline Package        ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

REM Step 1: Verify Ollama and model are available
echo [1/6] Verifying Ollama and AI model...
where ollama >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Ollama not found. Run setup.bat first.
    exit /b 1
)
ollama list | find /i "llama3.2" >nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: llama3.2 model not found. Run: ollama pull llama3.2:latest
    exit /b 1
)
echo       Ollama and model verified.
echo.

REM Step 2: Bundle Ollama for distribution
echo [2/6] Bundling Ollama for offline distribution...

if not exist "ollama-bundle" mkdir ollama-bundle

REM Copy Ollama executable
set "OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
if not exist "%OLLAMA_EXE%" (
    REM Try alternate location
    for /f "tokens=*" %%i in ('where ollama 2^>nul') do set "OLLAMA_EXE=%%i"
)
if exist "%OLLAMA_EXE%" (
    copy /y "%OLLAMA_EXE%" "ollama-bundle\ollama.exe" >nul
    echo       Copied ollama.exe
) else (
    echo WARNING: Could not find ollama.exe. AI Assistant will require separate Ollama install.
)

REM Copy Ollama runner/libs needed at runtime
set "OLLAMA_DIR=%LOCALAPPDATA%\Programs\Ollama"
if exist "%OLLAMA_DIR%\lib" (
    xcopy /s /y /i "%OLLAMA_DIR%\lib" "ollama-bundle\lib" >nul 2>nul
    echo       Copied Ollama libraries
)
if exist "%OLLAMA_DIR%\runners" (
    xcopy /s /y /i "%OLLAMA_DIR%\runners" "ollama-bundle\runners" >nul 2>nul
    echo       Copied Ollama runners
)

REM Copy the model files
set "OLLAMA_MODELS=%USERPROFILE%\.ollama\models"
if exist "%OLLAMA_MODELS%" (
    if not exist "ollama-bundle\models" mkdir "ollama-bundle\models"
    xcopy /s /y /i "%OLLAMA_MODELS%" "ollama-bundle\models" >nul 2>nul
    echo       Copied AI model files
) else (
    echo WARNING: Model files not found at %OLLAMA_MODELS%
    echo          AI Assistant will need to download the model on first run.
)
echo.

REM Step 3: Install Python dependencies
echo [3/6] Installing Python dependencies...
pip install pyinstaller "markitdown[all]" openai --quiet
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install Python dependencies.
    exit /b 1
)
echo       Done.
echo.

REM Step 4: Build Python backend
echo [4/6] Bundling Python backend with PyInstaller...
pyinstaller --distpath ./backend-dist --workpath ./build-backend --clean backend.spec --noconfirm
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: PyInstaller build failed.
    exit /b 1
)
echo       Done. Output: backend-dist\backend\backend.exe
echo.

REM Step 5: Install Node.js dependencies
echo [5/6] Installing Node.js dependencies...
call npm install --quiet
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: npm install failed.
    exit /b 1
)
echo       Done.
echo.

REM Step 6: Package with Electron Builder
echo [6/6] Packaging with Electron Builder...
call npx electron-builder --win
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Electron Builder failed.
    exit /b 1
)
echo       Done.
echo.

echo ╔══════════════════════════════════════════════════════════╗
echo ║  BUILD COMPLETE                                          ║
echo ╠══════════════════════════════════════════════════════════╣
echo ║                                                          ║
echo ║  Installer: dist\Content Analysis Setup *.exe            ║
echo ║  Portable:  dist\Content Analysis-Portable-*.exe         ║
echo ║                                                          ║
echo ║  The package includes:                                   ║
echo ║    - Application (Electron + Python backend)             ║
echo ║    - Ollama (local AI engine)                            ║
echo ║    - AI Model (llama3.2 for offline use)                 ║
echo ║                                                          ║
echo ║  Recipients do NOT need Python, Node.js, or internet.    ║
echo ║                                                          ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
