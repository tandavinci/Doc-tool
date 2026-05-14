@echo off
REM Build the Python backend into a standalone executable using PyInstaller.
REM Prerequisites: Python 3.8+ and PyInstaller must be installed.
REM   pip install pyinstaller

echo === Building Content Analysis Backend ===
echo.

pyinstaller --distpath ./backend-dist --workpath ./build-backend --clean backend.spec

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: PyInstaller build failed.
    echo Make sure PyInstaller is installed: pip install pyinstaller
    exit /b 1
)

echo.
echo === Backend build complete ===
echo Output: backend-dist\backend\backend.exe
echo.
