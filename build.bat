@echo off
REM Klatom Build Script (Simple)
python -m PyInstaller klatom.spec --clean --noconfirm
if errorlevel 1 (
    echo [ERROR] Build failed!
    pause
    exit /b 1
)
echo.
echo Build complete: dist\Klatom.exe
certutil -hashfile dist\Klatom.exe SHA256
pause
