@echo off
REM ew2 Build Script (Simple)
python -m PyInstaller klatom.spec --clean --noconfirm
if errorlevel 1 (
    echo [ERROR] Build failed!
    pause
    exit /b 1
)
echo.
echo Build complete: dist\ew2.exe
certutil -hashfile dist\ew2.exe SHA256
pause
