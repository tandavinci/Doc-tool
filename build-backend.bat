@echo off
REM Build the Python backend into a standalone executable using PyInstaller.
REM Prerequisites: Python 3.10+ and PyInstaller must be installed.
REM
REM This script:
REM   1. Installs markitdown[all] and other dependencies
REM   2. Runs PyInstaller to bundle everything into backend.exe
REM
REM The resulting backend.exe includes the MarkItDown library and all
REM its converters — no Python installation needed on the target machine.

echo === Building Content Analysis Backend ===
echo.

echo --- Installing dependencies ---
pip install pyinstaller "markitdown[all]" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Some dependencies may not have installed correctly.
    echo Continuing with build...
    echo.
)

echo.
echo --- Running PyInstaller ---
pyinstaller --distpath ./backend-dist --workpath ./build-backend --clean backend.spec

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: PyInstaller build failed.
    echo.
    echo Troubleshooting:
    echo   1. Ensure Python 3.10+ is installed
    echo   2. Run: pip install pyinstaller "markitdown[all]"
    echo   3. Try running this script again
    exit /b 1
)

echo.
echo === Backend build complete ===
echo Output: backend-dist\backend\backend.exe
echo.
echo Next step: Run "npm run dist" to package the full Electron app.
echo.
