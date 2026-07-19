#!/usr/bin/env python3
"""ew² – GitHub loader. Checks for updates and fetches config."""

from __future__ import annotations

import asyncio
import base64
import json
import sys
from pathlib import Path

import aiohttp

# GitHub repo URL (base64 encoded, not encrypted)
_GITHUB_URL_B64 = base64.b64encode(b"https://raw.githubusercontent.com/ew2k26/ew2/main/repo_data").decode()


def _get_base_url() -> str | None:
    """Decode the GitHub URL."""
    if not _GITHUB_URL_B64:
        return None
    try:
        return base64.b64decode(_GITHUB_URL_B64).decode()
    except Exception:
        return None


def _cache_dir() -> Path:
    from config import DATA_DIR
    d = DATA_DIR / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


async def _fetch(filename: str) -> str | None:
    base = _get_base_url()
    if not base:
        return None
    url = f"{base.rstrip('/')}/{filename}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return await resp.text()
    except Exception:
        pass
    return None


def _bundled_dir() -> Path | None:
    """Return the path to repo_data bundled in the exe (via PyInstaller --add-data)."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", "")) if hasattr(sys, "_MEIPASS") else None
        if base:
            bundled = base / "repo_data"
            if bundled.is_dir():
                return bundled
    local = Path(__file__).resolve().parent / "repo_data"
    if local.is_dir():
        return local
    return None


def _load_bundled(filename: str) -> str | None:
    """Load a file from the bundled repo_data directory."""
    d = _bundled_dir()
    if d is None:
        return None
    target = d / filename
    if target.exists():
        return target.read_text(encoding="utf-8")
    return None


async def fetch_names() -> list[str]:
    cache = _cache_dir() / "names.txt"
    content = await _fetch("names_to_check.txt")
    if content:
        names = [l.strip() for l in content.splitlines() if l.strip()]
        if names:
            cache.write_text("\n".join(names), encoding="utf-8")
            return names
    if cache.exists():
        cached = [l.strip() for l in cache.read_text(encoding="utf-8").splitlines() if l.strip()]
        if cached:
            return cached
    bundled = _load_bundled("names_to_check.txt")
    if bundled:
        return [l.strip() for l in bundled.splitlines() if l.strip()]
    return []


async def fetch_proxies() -> list[str]:
    cache = _cache_dir() / "proxies.txt"
    content = await _fetch("proxies.txt")
    if content:
        proxies = [l.strip() for l in content.splitlines() if l.strip()]
        if proxies:
            cache.write_text("\n".join(proxies), encoding="utf-8")
            return proxies
    if cache.exists():
        cached = [l.strip() for l in cache.read_text(encoding="utf-8").splitlines() if l.strip()]
        if cached:
            return cached
    bundled = _load_bundled("proxies.txt")
    if bundled:
        return [l.strip() for l in bundled.splitlines() if l.strip()]
    return []


async def fetch_config() -> dict:
    cache = _cache_dir() / "config.json"
    content = await _fetch("config.json")
    if content:
        try:
            data = json.loads(content)
            cache.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return data
        except Exception:
            pass
    if cache.exists():
        try:
            return json.loads(cache.read_text(encoding="utf-8"))
        except Exception:
            pass
    bundled = _load_bundled("config.json")
    if bundled:
        try:
            return json.loads(bundled)
        except Exception:
            pass
    return {}


async def fetch_all() -> dict:
    results = await asyncio.gather(
        fetch_config(), fetch_names(), fetch_proxies(),
        return_exceptions=True,
    )
    return {
        "config": results[0] if isinstance(results[0], dict) else {},
        "names": results[1] if isinstance(results[1], list) else [],
        "proxies": results[2] if isinstance(results[2], list) else [],
    }
