#!/usr/bin/env bash
set -euo pipefail

PYTHON="${PYTHON:-python3}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

cd "$SCRIPT_DIR"

echo "Building ew2 (main)..."
"$PYTHON" -m PyInstaller klatom.spec --clean --noconfirm

echo "Building ew2-Mod..."
"$PYTHON" -m PyInstaller ew2mod.spec --clean --noconfirm

echo ""
echo "Build complete:"
ls -lh dist/ew2 dist/ew2-Mod 2>/dev/null || ls -lh dist/ew2 dist/ew2-Mod.* 2>/dev/null

echo ""
echo "SHA256 checksums:"
sha256sum dist/ew2 dist/ew2-Mod 2>/dev/null || sha256sum dist/ew2* 2>/dev/null
