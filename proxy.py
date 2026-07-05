#!/usr/bin/env python3
"""Klatom – Proxy manager with auto-reset and circuit breaker."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

from config import C, load_lines


class ProxyManager:
    def __init__(self, proxies: list[str], remove_bad: bool = True) -> None:
        self.proxies = list(proxies)
        self.remove_bad = remove_bad
        self._errors: dict[str, int] = {}
        self._last_reset = time.time()
        self._reset_cooldown = 30

    def record_error(self, proxy: str) -> None:
        self._errors[proxy] = self._errors.get(proxy, 0) + 1
        if self.remove_bad and self._errors.get(proxy, 0) >= 3:
            if proxy in self.proxies:
                self.proxies.remove(proxy)

    def record_success(self, proxy: str) -> None:
        self._errors.pop(proxy, None)

    def get_proxy(self, index: int) -> str | None:
        if not self.proxies:
            return None
        return self.proxies[index % len(self.proxies)]

    def alive_count(self) -> int:
        return len(self.proxies)

    def should_reset(self) -> bool:
        if not self.proxies and time.time() - self._last_reset > self._reset_cooldown:
            return True
        return False

    async def reset_from_scrape(self, scraped: list[str]) -> int:
        if time.time() - self._last_reset < self._reset_cooldown:
            return 0
        self._last_reset = time.time()
        new = [p for p in scraped if p not in self.proxies]
        self.proxies.extend(new)
        self._errors.clear()
        return len(new)
