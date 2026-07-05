#!/usr/bin/env python3
"""Klatom – GitHub loader. Fetches everything from GitHub with encrypted URL."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import platform
import subprocess
import uuid
from pathlib import Path

import aiohttp

_GITHUB_URL_B64 = "tVDYKngeJdFr8NRZGzSmE5Y+SACY+165UHaYD0bop7GwC8kub0Bumn31jBwQPKYUjnNQEpTnEqRbcpI+Vqewvw=="
_FALLBACK_URL = ""

_GITHUB_URLS = [
    "https://raw.githubusercontent.com/etdddddd/klatom/main/repo_data",
    "https://raw.githubusercontent.com/etdddddd/klatom/master/repo_data",
]


def _hwid() -> str:
    parts = [platform.node(), platform.machine(), platform.processor(), str(uuid.getnode())]
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
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:24]


def _xor(data: bytes, key: bytes) -> bytes:
    klen = len(key)
    return bytes(b ^ key[i % klen] for i, b in enumerate(data))


def _derive_key() -> bytes:
    return hashlib.pbkdf2_hmac("sha256", _hwid().encode(), b"klatom-salt-v1", 100_000, dklen=32)


def encrypt_url(url: str) -> str:
    key = _derive_key()
    return base64.b64encode(_xor(url.encode(), key)).decode()


def decrypt_url() -> str | None:
    if _GITHUB_URL_B64:
        try:
            key = _derive_key()
            decrypted = _xor(base64.b64decode(_GITHUB_URL_B64), key).decode()
            if decrypted.startswith("http"):
                return decrypted
        except Exception:
            pass
    if _FALLBACK_URL and _FALLBACK_URL.startswith("http"):
        return _FALLBACK_URL
    for url in _GITHUB_URLS:
        if url:
            return url
    return None


def _cache_dir() -> Path:
    from config import DATA_DIR
    d = DATA_DIR / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


async def _fetch(filename: str) -> str | None:
    base = decrypt_url()
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


async def fetch_names() -> list[str]:
    cache = _cache_dir() / "names.txt"
    content = await _fetch("names_to_check.txt")
    if content:
        names = [l.strip() for l in content.splitlines() if l.strip()]
        if names:
            cache.write_text("\n".join(names), encoding="utf-8")
            return names
    if cache.exists():
        return [l.strip() for l in cache.read_text(encoding="utf-8").splitlines() if l.strip()]
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
        return [l.strip() for l in cache.read_text(encoding="utf-8").splitlines() if l.strip()]
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
