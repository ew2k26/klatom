#!/usr/bin/env python3
"""ew² v4.0 - Configuration, constants, helpers, and data models."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import platform
import string
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path

if getattr(sys, 'frozen', False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent
else:
    PROJECT_ROOT = Path(__file__).resolve().parent

# Cross-platform data directory
if sys.platform == "win32":
    APPDATA_DIR = Path.home() / "AppData" / "Local" / "ew2"
elif sys.platform == "darwin":
    APPDATA_DIR = Path.home() / "Library" / "Application Support" / "ew2"
else:
    # XDG Base Directory Specification for Linux
    _xdg_data = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    APPDATA_DIR = _xdg_data / "ew2"

DATA_DIR = APPDATA_DIR / "data"
LOGS_DIR = APPDATA_DIR / "logs"
RESULTS_DIR = APPDATA_DIR / "results"

VERSION = "4.0.0"
ENDPOINT = "https://discord.com/api/v9/unique-username/username-attempt-unauthed"
USERNAME_CHARS = string.ascii_lowercase + string.digits + "_" + "."
MAX_CONCURRENCY = 200

# Platform-aware font families
_system = platform.system()
if _system == "Windows":
    FONT_FAMILY = "Segoe UI"
    FONT_MONO = "Consolas"
elif _system == "Darwin":
    FONT_FAMILY = "Helvetica Neue"
    FONT_MONO = "Menlo"
else:
    # Linux: try common fonts, fallback to system default
    FONT_FAMILY = "DejaVu Sans"
    FONT_MONO = "DejaVu Sans Mono"


class C:
    PRIMARY   = "#3A3A3A"
    PRIMARY_D = "#2A2A2A"
    SUCCESS   = "#28C840"
    DANGER    = "#E03030"
    WARNING   = "#E08800"
    MUTED     = "#555560"
    BORDER    = "#1A1A24"
    BG        = "#050508"


def get_hwid_parts() -> list[str]:
    """Return platform-specific hardware identifier parts."""
    parts = [platform.node(), platform.machine(), platform.processor(), str(uuid.getnode())]
    if sys.platform == "win32":
        for cmd, field in [
            (["wmic", "baseboard", "get", "serialnumber"], "SerialNumber"),
            (["wmic", "diskdrive", "get", "serialnumber"], "SerialNumber"),
            (["wmic", "bios", "get", "serialnumber"], "SerialNumber"),
        ]:
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                for line in r.stdout.splitlines():
                    s = line.strip()
                    if s and s != field:
                        parts.append(s)
                        break
            except Exception:
                pass
    elif sys.platform == "linux":
        for path in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
            try:
                mid = Path(path).read_text().strip()
                if mid:
                    parts.append(mid)
                    break
            except Exception:
                pass
        try:
            puuid = Path("/sys/class/dmi/id/product_uuid").read_text().strip()
            if puuid:
                parts.append(puuid)
        except Exception:
            pass
    elif sys.platform == "darwin":
        try:
            r = subprocess.run(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                capture_output=True, text=True, timeout=5,
            )
            for line in r.stdout.splitlines():
                if "IOPlatformSerialNumber" in line:
                    serial = line.split('"')[-2]
                    if serial:
                        parts.append(serial)
                    break
        except Exception:
            pass
    return parts


def ensure_dir(*paths: str | Path) -> None:
    for p in paths:
        Path(p).mkdir(parents=True, exist_ok=True)


def ensure_file(filepath: str | Path, *, clean: bool = False) -> None:
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    if clean or not path.exists():
        path.write_text("", encoding="utf-8")


def load_lines(filepath: str | Path) -> list[str]:
    path = Path(filepath)
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def is_valid_username(name: str) -> bool:
    if not (2 <= len(name) <= 32):
        return False
    if ".." in name:
        return False
    if name.startswith(".") or name.endswith("."):
        return False
    return all(c in USERNAME_CHARS for c in name)


class Config:
    def __init__(self, path: str | Path | None = None) -> None:
        self._path = Path(path) if path else DATA_DIR / "config.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists() and self._path.stat().st_size > 0:
            try:
                self._data = json.loads(self._path.read_text(encoding="utf-8"))
            except Exception:
                self._data = {}
        else:
            self._path.write_text("{}", encoding="utf-8")

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        self._data[key] = value
        self._path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def get_masked(self, key: str, default=None) -> str:
        val = self._data.get(key, default)
        if not val or not isinstance(val, str):
            return val
        if "webhook" in key.lower() or "discord.com/api/webhooks" in val:
            parts = val.rsplit("/", 1)
            if len(parts) == 2 and len(parts[1]) > 8:
                return parts[0] + "/" + "\u2022" * (len(parts[1]) - 8) + parts[1][-8:]
        return val

    def get_all(self) -> dict:
        return dict(self._data)


@dataclass
class AppSettings:
    debug: bool = False
    verbose: bool = False
    no_wizard: bool = False
    mod: bool = False
    terminal: bool = False


@dataclass
class RunConfig:
    proxies: list[str]
    remove_bad_proxies: bool
    usernames: list[str]
    concurrency: int
    timeout: int
    scraped: bool = False
    webhook_url: str | None = None
    webhook_message: str | None = None


@dataclass
class Stats:
    requests: int = 0
    works: int = 0
    taken: int = 0
    ratelimited: int = 0
    errors: int = 0
    circuit_opens: int = 0
    rps: float = 0.0
    checks_rps: float = 0.0
    peak_rps: float = 0.0
    best_streak: int = 0
    _streak: int = 0
    _lock: field(default_factory=lambda: asyncio.Lock) = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        import asyncio
        self._lock = asyncio.Lock()

    async def inc_requests(self) -> None:
        async with self._lock:
            self.requests += 1

    async def inc_works(self) -> None:
        async with self._lock:
            self.works += 1
            self._streak += 1
            if self._streak > self.best_streak:
                self.best_streak = self._streak

    async def inc_taken(self) -> None:
        async with self._lock:
            self.taken += 1
            self._streak = 0

    async def inc_ratelimited(self) -> None:
        async with self._lock:
            self.ratelimited += 1

    async def inc_errors(self) -> None:
        async with self._lock:
            self.errors += 1

    async def inc_circuit_open(self) -> None:
        async with self._lock:
            self.circuit_opens += 1

    async def set_rps(self, value: float) -> None:
        async with self._lock:
            self.rps = value
            if value > self.peak_rps:
                self.peak_rps = value

    async def set_checks_rps(self, value: float) -> None:
        async with self._lock:
            self.checks_rps = value

    async def snapshot(self) -> dict:
        async with self._lock:
            return {
                "requests": self.requests,
                "works": self.works,
                "taken": self.taken,
                "ratelimited": self.ratelimited,
                "errors": self.errors,
                "circuit_opens": self.circuit_opens,
                "rps": self.rps,
                "checks_rps": self.checks_rps,
                "peak_rps": self.peak_rps,
                "best_streak": self.best_streak,
            }
