#!/usr/bin/env python3
"""ew² v4.0 - Proxy manager with rotation, cooldowns, scoring, speed testing, and scraping."""

from __future__ import annotations

import asyncio
import itertools
import random
import re
import time
from urllib.parse import urlparse

import aiohttp

from config import ENDPOINT

_VALID_PROXY = re.compile(
    r"^https?://(?:[^@\s]+@)?[a-zA-Z0-9](?:[a-zA-Z0-9\-.]*[a-zA-Z0-9])?:\d{1,5}$"
)

_PROXY_RE = re.compile(
    r"^(?:https?://)?(?:[^@\s]+@)?[a-zA-Z0-9](?:[a-zA-Z0-9\-.]*[a-zA-Z0-9])?:\d{1,5}$"
)

_SCRAPE_SOURCES: list[tuple[str, str]] = [
    ("TheSpeedX",       "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"),
    ("monosans",        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt"),
    ("proxifly",        "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt"),
    ("ShiftyTR-http",   "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt"),
    ("ShiftyTR-https",  "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/https.txt"),
    ("roosterkid",      "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt"),
    ("sunny9577",       "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/generated/http_proxies.txt"),
    ("rdavydov",        "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/http.txt"),
    ("Anonym0usWork12", "https://raw.githubusercontent.com/Anonym0usWork12/Proxy-List/master/http.txt"),
    ("officialputuid",  "https://raw.githubusercontent.com/officialputuid/rules/master/proxies.txt"),
    ("mmpx12-http",     "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt"),
    ("mmpx12-https",    "https://raw.githubusercontent.com/mmpx12/proxy-list/master/https.txt"),
    ("iplocate-http",   "https://raw.githubusercontent.com/iplocate/free-proxy-list/main/protocols/http.txt"),
    ("iplocate-https",  "https://raw.githubusercontent.com/iplocate/free-proxy-list/main/protocols/https.txt"),
    ("openproxylist",   "https://api.openproxylist.xyz/http.txt"),
    ("proxyscrape",     "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all"),
    ("geonode",         "https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&protocols=http%2Chttps"),
]


async def scrape_proxies(
    sources: list[tuple[str, str]] | None = None,
    timeout: float = 10.0,
    on_progress=None,
) -> list[str]:
    """Scrape free proxies from public sources. Returns deduplicated in-memory list.

    Args:
        sources: List of (name, url) tuples. Defaults to _SCRAPE_SOURCES.
        timeout: Per-source HTTP timeout in seconds.
        on_progress: Optional callback(name, found_count, status_str).

    Returns:
        List of unique proxy strings (ip:port or protocol://ip:port).
        Never raises — failed sources are skipped gracefully.
    """
    if sources is None:
        sources = _SCRAPE_SOURCES

    async def _fetch_one(name: str, url: str) -> list[str]:
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=timeout),
                trust_env=False,
            ) as sess:
                async with sess.get(url) as resp:
                    if resp.status != 200:
                        if on_progress:
                            on_progress(name, 0, f"HTTP {resp.status}")
                        return []
                    text = await resp.text()
                    found = [p.strip() for p in text.splitlines()
                             if _PROXY_RE.match(p.strip())]
                    if on_progress:
                        on_progress(name, len(found), "ok")
                    return found
        except Exception as e:
            if on_progress:
                on_progress(name, 0, str(e)[:60])
            return []

    tasks = [_fetch_one(name, url) for name, url in sources]
    results = await asyncio.gather(*tasks)

    seen: set[str] = set()
    all_proxies: list[str] = []
    for batch in results:
        for p in batch:
            key = p.split("@")[-1] if "@" in p else p
            if key not in seen:
                seen.add(key)
                all_proxies.append(p)

    return all_proxies


def scrape_proxies_sync(
    sources: list[tuple[str, str]] | None = None,
    timeout: float = 10.0,
    on_progress=None,
) -> list[str]:
    """Synchronous wrapper around scrape_proxies for non-async contexts."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            scrape_proxies(sources=sources, timeout=timeout, on_progress=on_progress)
        )
    except Exception:
        return []
    finally:
        loop.close()


class ProxyManager:
    """Manages proxy rotation with per-proxy ratelimit cooldowns, scoring, and speed testing."""

    def __init__(
        self,
        proxies: list[str],
        remove_on_fail: bool = True,
        scored: bool = False,
    ) -> None:
        cleaned = [p.strip() if p else None for p in proxies]
        self._proxies: list[str | None] = cleaned if cleaned else [None]
        self._proxyless = all(p is None for p in self._proxies)
        self._cycle = itertools.cycle(self._proxies)
        self._dead: set[str] = set()
        self._cooldowns: dict[str, float] = {}
        self.remove_on_fail = remove_on_fail
        self._lock = asyncio.Lock()

        # scoring (scraped free proxies only)
        self._scored = scored
        self._scores: dict[str, int] = {}
        self._rate_limited_until: dict[str, float] = {}
        # latency tracking: proxy -> avg latency in seconds
        self._latencies: dict[str, float] = {}
        self._latency_count: dict[str, int] = {}
        if scored:
            for raw in self._proxies:
                if raw and raw.strip():
                    key = self._format(raw) or raw.strip()
                    self._scores[key] = 5

    # ── Properties ──

    @property
    def is_proxyless(self) -> bool:
        return self._proxyless

    @property
    def is_single(self) -> bool:
        return len(self._proxies) == 1 and not self._proxyless

    @property
    def alive_count(self) -> int:
        if self.is_single:
            return 1
        if self._scored:
            return sum(1 for k, v in self._scores.items() if v > 0 and k not in self._dead)
        return max(0, len(self._proxies) - len(self._dead))

    @property
    def total_count(self) -> int:
        return len(self._proxies)

    @property
    def dead_count(self) -> int:
        return len(self._dead)

    @property
    def avg_latency(self) -> float:
        if not self._latencies:
            return 0.0
        return sum(self._latencies.values()) / len(self._latencies)

    # ── Formatting ──

    @staticmethod
    def _format(raw: str | None) -> str | None:
        if raw is None:
            return None
        raw = raw.strip()
        return f"http://{raw}" if not raw.startswith("http") else raw

    # ── Core: next proxy ──

    async def next(self) -> str | None:
        if self._proxyless:
            return None

        if self.is_single:
            return self._format(self._proxies[0])

        # Scored path (scraped free proxies) – weighted random with latency preference
        if self._scored:
            while True:
                async with self._lock:
                    live = {
                        k: v for k, v in self._scores.items()
                        if k and v > 0
                        and k not in self._dead
                        and (k not in self._cooldowns or time.time() >= self._cooldowns.get(k, 0))
                        and (k not in self._rate_limited_until or time.time() >= self._rate_limited_until.get(k, 0))
                    }
                    if not live:
                        return None
                    keys = list(live.keys())
                    # prefer low-latency proxies
                    weights = []
                    for k in keys:
                        w = live[k]
                        lat = self._latencies.get(k)
                        if lat is not None and lat > 0:
                            # faster proxies get higher weight
                            w = max(1, int(w * (1.0 / max(lat, 0.1))))
                        weights.append(w)
                    total_w = sum(weights)
                    pick = random.uniform(0, total_w) if total_w > 0 else 0
                    acc = 0
                    for i, k in enumerate(keys):
                        acc += weights[i]
                        if acc >= pick:
                            return k
                    return keys[-1]

        # Static multi-proxy path
        while True:
            async with self._lock:
                if len(self._dead) >= len(self._proxies):
                    return None

                for _ in range(len(self._proxies) * 2):
                    raw = next(self._cycle)
                    proxy = self._format(raw) if raw else None
                    key = proxy or ""
                    if key in self._dead:
                        continue
                    if key in self._cooldowns and time.time() < self._cooldowns[key]:
                        continue
                    return proxy

                now = time.time()
                earliest = min(
                    (v for v in self._cooldowns.values() if v > now),
                    default=now + 1,
                )
                wait = max(earliest - now, 0.2)

            await asyncio.sleep(wait)

    # ── Latency tracking ──

    def record_latency(self, proxy: str | None, latency: float) -> None:
        if not proxy:
            return
        key = proxy
        if key in self._scores or not self._scored:
            count = self._latency_count.get(key, 0)
            old = self._latencies.get(key, 0.0)
            # exponential moving average
            if count == 0:
                self._latencies[key] = latency
            else:
                alpha = 0.3
                self._latencies[key] = old * (1 - alpha) + latency * alpha
            self._latency_count[key] = count + 1

    # ── Scoring API ──

    def score_hit(self, proxy: str | None) -> None:
        if not self._scored or not proxy:
            return
        key = proxy
        if key in self._scores:
            self._scores[key] = min(self._scores[key] + 5, 100)

    def set_rate_limit(self, proxy: str | None, seconds: float) -> None:
        if not self._scored or not proxy:
            return
        key = proxy
        if key in self._scores:
            self._rate_limited_until[key] = time.time() + seconds

    def score_miss(self, proxy: str | None) -> None:
        if not self._scored or not proxy:
            return
        key = proxy
        if key in self._scores:
            self._scores[key] -= 1
            if self._scores[key] <= 0:
                self._dead.add(key)
                del self._scores[key]
                self._latencies.pop(key, None)
                self._latency_count.pop(key, None)

    async def mark_dead(self, proxy: str | None) -> None:
        if not self.remove_on_fail or proxy is None:
            return
        async with self._lock:
            self._dead.add(proxy)

    async def set_cooldown(self, proxy: str | None, seconds: float) -> None:
        if proxy is None:
            return
        async with self._lock:
            self._cooldowns[proxy] = time.time() + seconds

    # ── Speed test ──

    async def speed_test(
        self,
        concurrency: int = 100,
        timeout: float = 5.0,
        on_progress=None,
    ) -> list[tuple[str, float, bool]]:
        """Test all proxies for latency and availability.

        Returns list of (proxy, latency_ms, is_working) sorted by latency.
        Calls on_progress(tested, total, working) periodically.
        """
        sem = asyncio.Semaphore(concurrency)
        results: list[tuple[str, float, bool]] = []
        tested = [0]
        working_count = [0]
        lock = asyncio.Lock()
        total = len(self._proxies)

        async def _test_one(proxy_raw: str | None) -> None:
            proxy = self._format(proxy_raw) if proxy_raw else None
            if proxy and not _VALID_PROXY.match(proxy):
                async with lock:
                    tested[0] += 1
                    results.append((proxy or "", 99999.0, False))
                if on_progress and tested[0] % 50 == 0:
                    on_progress(tested[0], total, working_count[0])
                return

            is_ok = False
            start = time.time()
            try:
                async with sem:
                    start = time.time()
                    async with aiohttp.ClientSession(
                        timeout=aiohttp.ClientTimeout(total=timeout),
                        trust_env=False,
                    ) as sess:
                        async with sess.post(
                            ENDPOINT,
                            json={"username": "a"},
                            proxy=proxy,
                            headers={"Content-Type": "application/json"},
                        ) as resp:
                            is_ok = resp.status in (200, 201, 204, 400, 429)
            except Exception:
                pass

            latency_ms = (time.time() - start) * 1000
            async with lock:
                tested[0] += 1
                if is_ok:
                    working_count[0] += 1
                results.append((proxy or "", latency_ms, is_ok))
                if on_progress and tested[0] % 50 == 0:
                    on_progress(tested[0], total, working_count[0])

        tasks = [_test_one(p) for p in self._proxies]
        await asyncio.gather(*tasks)

        results.sort(key=lambda x: (not x[2], x[1]))

        for proxy, latency_ms, is_ok in results:
            if is_ok and latency_ms < 99999:
                self._latencies[proxy] = latency_ms / 1000.0
                self._latency_count[proxy] = 1

        if on_progress:
            on_progress(total, total, working_count[0])

        return results

    async def apply_speed_results(self, results: list[tuple[str, float, bool]], remove_slow: bool = True, max_latency_ms: float = 3000.0) -> int:
        """Apply speed test results. Removes dead/slow proxies. Returns count of working proxies."""
        async with self._lock:
            working = 0
            for proxy, latency_ms, is_ok in results:
                if not is_ok or latency_ms >= 99999:
                    self._dead.add(proxy)
                    self._scores.pop(proxy, None)
                    self._latencies.pop(proxy, None)
                    self._latency_count.pop(proxy, None)
                elif remove_slow and latency_ms > max_latency_ms:
                    self._dead.add(proxy)
                    self._scores.pop(proxy, None)
                else:
                    working += 1
                    if proxy in self._scores:
                        # boost score for fast proxies
                        speed_bonus = max(1, int(5 * (1.0 - latency_ms / max_latency_ms)))
                        self._scores[proxy] = min(self._scores[proxy] + speed_bonus, 100)
            return working

    # ── Validation ──

    async def validate(
        self,
        timeout: float = 15.0,
        concurrency: int = 200,
        sample: int | None = None,
    ) -> tuple[int, int]:
        async def _test_one(proxy_raw: str | None) -> bool:
            proxy = self._format(proxy_raw) if proxy_raw else None
            if proxy and not _VALID_PROXY.match(proxy):
                return False
            try:
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=timeout),
                    trust_env=False,
                ) as sess:
                    async with sess.post(
                        ENDPOINT,
                        json={"username": "a"},
                        proxy=proxy,
                        headers={"Content-Type": "application/json"},
                    ) as resp:
                        return resp.status in (200, 201, 204)
            except Exception:
                return False

        sem = asyncio.Semaphore(concurrency)

        async def _test_with_limit(p: str) -> bool:
            async with sem:
                return await _test_one(p)

        pool = self._proxies[:]
        if sample is not None:
            pool = random.sample(pool, min(sample, len(pool)))

        tasks = [_test_with_limit(p) for p in pool]
        results = await asyncio.gather(*tasks)
        return sum(results), len(pool)
