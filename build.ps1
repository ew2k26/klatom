# Klatom Build Script (PowerShell)
# Requires: Python 3.10+, pip

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Klatom Build Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python not found. Install Python 3.10+" -ForegroundColor Red
    exit 1
}

# Check/install PyInstaller
$pyinstaller = pip show pyinstaller 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[INFO] Installing PyInstaller..." -ForegroundColor Yellow
    pip install pyinstaller --quiet
}

# Install dependencies
Write-Host "[INFO] Installing dependencies..." -ForegroundColor Yellow
pip install aiohttp rich --quiet

# Clean previous build
Write-Host "[INFO] Cleaning previous build..." -ForegroundColor Yellow
if (Test-Path dist) { Remove-Item -Recurse -Force dist }
if (Test-Path build) { Remove-Item -Recurse -Force build }

# Build
Write-Host "[INFO] Building Klatom (onefile)..." -ForegroundColor Yellow
python -m PyInstaller klatom.spec --clean --noconfirm

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Build failed!" -ForegroundColor Red
    exit 1
}

# Generate checksum
Write-Host "[INFO] Generating checksum..." -ForegroundColor Yellow
$hash = (Get-FileHash -Path dist\Klatom.exe -Algorithm SHA256).Hash.ToLower()

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Build complete!" -ForegroundColor Green
Write-Host "  Output: dist\Klatom.exe" -ForegroundColor Green
Write-Host "  Size: $([math]::Round((Get-Item dist\Klatom.exe).Length / 1MB, 2)) MB" -ForegroundColor Green
Write-Host "  SHA-256: $hash" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Save checksum to file
$hash | Out-File -FilePath dist\checksum.txt -Encoding utf8
Write-Host "[INFO] Checksum saved to dist\checksum.txt" -ForegroundColor Yellow
