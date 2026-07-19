# ew²

![Version](https://img.shields.io/badge/version-4.0.0-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/license-Proprietary-red)

**Fast, offline Discord username checker with async engine and circuit breaker.**

![ew² Logo](ew2_icon.png)

---

## Features

- 🚀 **Async Engine** — Up to 200 concurrent workers for high-speed checking
- 🔄 **Circuit Breaker** — Automatic proxy rotation on failure thresholds
- 🛡️ **Proxy Rotation** — Built-in proxy management with speed testing
- 🔔 **Webhook Notifications** — Discord webhook alerts for results
- 🧙 **Interactive Wizard** — Step-by-step setup for first-time users
- 🔐 **Encrypted Auth** — HWID-locked tokens with XOR + HMAC storage
- 🖥️ **Modern GUI** — Dark-themed PySide6 interface with real-time stats
- 📦 **Offline-Ready** — All data bundled; no internet required to run
- ⚡ **Single Executable** — No dependencies, no installation needed
- 🔍 **Speed Test** — Built-in proxy speed testing with scraped data

---

## Quick Start

1. **Download** `ew2.exe` from the releases page
2. **Verify** the checksum:
   ```bash
   certutil -hashfile ew2.exe SHA256
   ```
3. **Run** `ew2.exe`
4. **Enter** your token or select the 24h free trial

---

## System Requirements

| Requirement | Details |
|-------------|---------|
| OS | Windows 10+ (64-bit) or Linux |
| RAM | 512 MB minimum |
| Disk | 50 MB free space |
| Network | Not required (offline operation) |
| Dependencies | None — single self-contained executable |

---

## Installation

### Windows

```bash
# Download the latest release
# Extract to any folder
# Run ew2.exe
```

Or build from source:

```bash
git clone https://github.com/your-repo/ew2.git
cd ew2
pip install pyinstaller aiohttp rich PySide6
.\build.bat
```

Output: `dist\ew2.exe`

### Linux

```bash
git clone https://github.com/your-repo/ew2.git
cd ew2
pip install pyinstaller aiohttp rich PySide6
chmod +x build.sh
./build.sh
```

Output: `dist/ew2`

---

## Configuration

All configuration is stored in:

| Platform | Path |
|----------|------|
| Windows | `%LOCALAPPDATA%\ew2\` |
| macOS | `~/Library/Application Support/ew2/` |
| Linux | `~/.local/share/ew2/` |

### Directory Structure

```
ew2/
├── data/          # Config, proxy lists, username lists
├── logs/          # Runtime logs
└── results/       # Check results output
```

### Configuration File

Located at `data/config.json`. Example settings:

```json
{
  "concurrency": 200,
  "timeout": 10,
  "webhook_url": "https://discord.com/api/webhooks/...",
  "remove_bad_proxies": true
}
```

---

## Building from Source

### Prerequisites

- **Python 3.10+**
- **pip** (Python package manager)
- **PyInstaller** (build tool)
- **Git** (version control)

### Install Dependencies

```bash
pip install pyinstaller aiohttp rich PySide6
```

### Build Commands

**Windows (batch):**
```bash
build.bat
```

**Windows (PowerShell):**
```powershell
.\build.ps1
```

**Linux/macOS:**
```bash
chmod +x build.sh
./build.sh
```

### Build Output

| Mode | Output |
|------|--------|
| ONEDIR (default) | `dist/ew2/ew2.exe` |
| Checksum | `dist/checksum.txt` |

### Verify Build

```bash
# Windows
certutil -hashfile dist\ew2.exe SHA256

# Linux
sha256sum dist/ew2
```

---

## Security

- 🔒 **Single executable** — No external dependencies to tamper with
- 🛡️ **Encrypted storage** — Auth tokens encrypted with XOR + HMAC integrity
- 🆔 **HWID binding** — Trial sessions locked to hardware
- ✅ **SHA-256 verification** — Checksum validation for all releases
- 🌐 **HTTPS-only** — All network communications encrypted
- 🔑 **Token prefix** — All valid tokens start with `EW2-`

---

## Offline Operation

ew² does not require internet to function. All necessary data (username lists, proxy samples, configuration) is bundled inside the executable. Internet connections are optional and used only to fetch updates if available.

---

## Troubleshooting

### Build fails with "Python not found"

Ensure Python 3.10+ is installed and added to your PATH:

```bash
python --version
```

### Windows Defender flags the executable

This is a false positive common with PyInstaller builds. The executable is safe. You can whitelist it in Windows Defender settings.

### GUI doesn't appear

Ensure PySide6 is installed:

```bash
pip install PySide6
```

### Checksum doesn't match

Re-download the file from the official source. If the issue persists, open an issue on GitHub.

### Proxy errors

- Ensure your proxy list is valid (format: `ip:port` or `ip:port:user:pass`)
- Run the built-in speed test to filter bad proxies
- Enable `remove_bad_proxies` in config

---

## Discord Community

Join the community for support, updates, and discussion:

🔗 [Join our Discord](https://discord.gg/ew2)

---

## License

Proprietary. All rights reserved.

Unauthorized copying, modification, or distribution of this software is strictly prohibited.
