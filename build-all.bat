@echo off
REM ═══════════════════════════════════════════════════════════════
REM  ONE-STEP BUILD: Documentation AI Tool
REM ═══════════════════════════════════════════════════════════════
REM
REM  This script builds the complete standalone application:
REM    1. Bundles Python backend (including MarkItDown) into backend.exe
REM    2. Packages everything into an installable Windows app
REM
REM  Prerequisites (build machine only):
REM    - Python 3.10+
REM    - Node.js 18+
REM    - npm
REM
REM  The output is a standalone installer/portable .exe that works
REM  on any Windows machine WITHOUT Python or Node.js installed.
REM ═══════════════════════════════════════════════════════════════

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║  Building Documentation AI Tool - Standalone Package     ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

REM Step 1: Install Python dependencies
echo [1/4] Installing Python dependencies...
pip install pyinstaller "markitdown[all]" --quiet
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install Python dependencies.
    echo Ensure Python 3.10+ and pip are available.
    exit /b 1
)
echo       Done.
echo.

REM Step 2: Build Python backend
echo [2/4] Bundling Python backend with PyInstaller...
pyinstaller --distpath ./backend-dist --workpath ./build-backend --clean backend.spec --noconfirm
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: PyInstaller build failed.
    exit /b 1
)
echo       Done. Output: backend-dist\backend\backend.exe
echo.

REM Step 3: Install Node.js dependencies
echo [3/4] Installing Node.js dependencies...
call npm install --quiet
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: npm install failed.
    exit /b 1
)
echo       Done.
echo.

REM Step 4: Package with Electron Builder
echo [4/4] Packaging with Electron Builder...
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
echo ║  Share either file. Recipients do NOT need Python        ║
echo ║  or Node.js installed.                                   ║
echo ║                                                          ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
