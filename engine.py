#!/usr/bin/env python3
"""Klatom – Checker engine with circuit breaker."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

import aiohttp

from config import C, ENDPOINT, RunConfig, Stats


class Checker:
    def __init__(self, cfg: RunConfig, stats: Stats, webhook_url: str = "",
                 webhook_msg: str = "**<name>** available | <t:time:R>") -> None:
        self.cfg = cfg
        self.stats = stats
        self.webhook_url = webhook_url
        self.webhook_msg = webhook_msg
        self.session: aiohttp.ClientSession | None = None
        self.url = ENDPOINT
        self._circuit_open = False
        self._circuit_until = 0.0
        self._consecutive_errors: dict[str, int] = {}
        self._hits_batch: list[str] = []
        self._batch_lock = asyncio.Lock()
        self._batch_timer: asyncio.Task | None = None

    async def start(self) -> None:
        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=min(self.cfg.concurrency * 2, 500)),
            timeout=aiohttp.ClientTimeout(total=self.cfg.timeout),
        )

    async def close(self) -> None:
        if self.session:
            await self.session.close()
        if self._batch_timer:
            self._batch_timer.cancel()

    async def check(self, username: str) -> tuple[str, str]:
        if self._circuit_open:
            if time.time() < self._circuit_until:
                return "CIRCUIT", username
            self._circuit_open = False

        proxy = None
        if self.cfg.proxies:
            idx = hash(username) % len(self.cfg.proxies)
            proxy = self.cfg.proxies[idx]

        try:
            async with self.session.post(
                self.url,
                json={"username": username},
                proxy=proxy,
            ) as resp:
                await self.stats.inc_requests()
                status = resp.status

                if status == 200:
                    await self.stats.inc_works()
                    self._consecutive_errors.clear()
                    await self._on_hit(username)
                    return "HIT", username

                if status in (404, 400):
                    await self.stats.inc_taken()
                    self._consecutive_errors.clear()
                    return "TAKEN", username

                if status == 429:
                    await self.stats.inc_ratelimited()
                    self._record_error(proxy)
                    return "RATE", username

                self._record_error(proxy)
                return "ERROR", username

        except (aiohttp.ClientError, asyncio.TimeoutError):
            await self.stats.inc_requests()
            self._record_error(proxy)
            return "ERROR", username

    def _record_error(self, proxy: str | None) -> None:
        if not proxy:
            return
        self._consecutive_errors[proxy] = self._consecutive_errors.get(proxy, 0) + 1
        if self._consecutive_errors[proxy] >= 3:
            if proxy in self.cfg.proxies:
                self.cfg.proxies.remove(proxy)
            self._consecutive_errors.pop(proxy, None)

    def open_circuit(self, seconds: float = 5.0) -> None:
        self._circuit_open = True
        self._circuit_until = time.time() + seconds

    async def _on_hit(self, username: str) -> None:
        async with self._batch_lock:
            self._hits_batch.append(username)
            if len(self._hits_batch) >= 10:
                await self._flush_hits()

    async def _flush_hits(self) -> None:
        if not self._hits_batch or not self.webhook_url:
            return
        batch = self._hits_batch[:]
        self._hits_batch.clear()
        try:
            lines = [self.webhook_msg.replace("<name>", u) for u in batch]
            async with aiohttp.ClientSession() as s:
                async with s.post(self.webhook_url, json={"content": "\n".join(lines)}):
                    pass
        except Exception:
            pass

    async def flush_remaining(self) -> None:
        async with self._batch_lock:
            await self._flush_hits()
