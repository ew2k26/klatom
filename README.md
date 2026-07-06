# Klatom

Discord Username Checker v3.1.0

## Quick Start

1. Download `Klatom.exe`
2. Verify checksum: `certutil -hashfile Klatom.exe SHA256`
3. Run `Klatom.exe`
4. Enter your token or select 24h free trial

## Features

- Async engine with up to 2000 concurrent workers
- Circuit breaker and proxy rotation
- Discord webhook notifications
- Interactive setup wizard
- HWID-locked tokens with encrypted storage
- Works fully offline with bundled data

## Offline Operation

Klatom does not require internet to function. All necessary data (username lists, proxy samples, configuration) is bundled inside the executable. Internet connections are optional and used only to fetch updates if available.

## System Requirements

- Windows 10+ (64-bit)
- No additional software required

## Data Location

All data is stored in: `%LOCALAPPDATA%\Klatom\`

## Security

- Single executable, no dependencies
- Encrypted auth storage (AES + HMAC)
- HWID-bound trial sessions
- SHA-256 checksum verification
- HTTPS for all network communications

## Building from Source

```
pip install pyinstaller aiohttp rich
build.bat
```

Output: `dist\Klatom\Klatom.exe`

## License

Proprietary. All rights reserved.
