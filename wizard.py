#!/usr/bin/env python3
"""ew² v4.0 - Setup wizard and proxy scraper."""

from __future__ import annotations

import asyncio
import itertools
import random
import sys
from pathlib import Path

from rich.prompt import Confirm, IntPrompt, Prompt

from config import (
    DATA_DIR,
    MAX_CONCURRENCY,
    PROJECT_ROOT,
    USERNAME_CHARS,
    AppSettings,
    Config,
    RunConfig,
    ensure_dir,
    ensure_file,
    is_valid_username,
    load_lines,
)
from ui import (
    C,
    banner,
    card,
    config_summary,
    console,
    fail,
    info,
    info_card,
    ok,
    progress_steps,
    section,
    speed_test_result,
    warn_card,
)

DEFAULT_PROXY_FILE = str(DATA_DIR / "proxies.txt")
DEFAULT_NAMES_FILE = str(DATA_DIR / "names_to_check.txt")

_PROXY_FILE_DISPLAY = "data/proxies.txt"
_NAMES_FILE_DISPLAY = "data/names_to_check.txt"


def _resolve_input_path(raw: str) -> str:
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return str(p)



# ---------------------------------------------------------------------------
# Setup wizard – main entry
# ---------------------------------------------------------------------------

async def setup_wizard(config: Config, settings: AppSettings) -> RunConfig:
    console.clear()
    console.print(banner())
    console.print()
    console.print(progress_steps(0))

    # Step 1: Proxies
    warn_card(
        f"[{C.WARNING}]Proxies strongly recommended[/]",
        f"[{C.MUTED}]Without them Discord will rate-limit you.[/]",
        f"[{C.MUTED}]Format: login:pass@host:port[/]",
    )
    proxies, remove_bad, scraped = await _step_proxies(config)

    # Step 2: Speed test (scraped only)
    console.print()
    console.print(progress_steps(1))
    working_proxies = 0
    if scraped and len(proxies) > 10:
        working_proxies = await _step_speed_test(proxies, config)
    elif scraped:
        ok(f"{len(proxies)} proxies loaded (too few for speed test)")

    # Step 3: Usernames
    console.print()
    console.print(progress_steps(2))
    usernames = _step_usernames()

    # Step 4: Speed settings
    console.print()
    console.print(progress_steps(3))
    concurrency, timeout = _step_speed(proxies, scraped)

    # Step 5: Webhook
    console.print()
    console.print(progress_steps(4))
    webhook_url, webhook_msg = _step_webhook(config)

    config.set("timeout", timeout)
    config.set("concurrency", concurrency)
    config.set("remove_proxies", remove_bad)

    # Summary
    config_summary(
        proxy_count=len(proxies),
        scraped=scraped,
        remove_bad=remove_bad,
        username_count=len(usernames),
        concurrency=concurrency,
        timeout=timeout,
        webhook=bool(webhook_url),
        working_proxies=working_proxies,
    )

    if not Confirm.ask(f"\n[{C.PRIMARY}]Start checking?[/]", default=True):
        console.print(f"[{C.MUTED}]Aborted.[/]")
        sys.exit(0)

    return RunConfig(
        proxies=proxies,
        remove_bad_proxies=remove_bad,
        usernames=usernames,
        concurrency=concurrency,
        timeout=timeout,
        scraped=scraped,
        webhook_url=webhook_url,
        webhook_message=webhook_msg,
    )


# ---------------------------------------------------------------------------
# Step 1: Proxies
# ---------------------------------------------------------------------------

async def _step_proxies(config: Config) -> tuple[list[str], bool, bool]:
    proxies: list[str] = []
    remove_bad = False
    scraped = False

    if not proxies:
        console.print()
        mode = Prompt.ask(
            f"[{C.PRIMARY}]Proxy source:[/] (f)ile  (p)aste  (s)crape  (n)one",
            choices=["f", "p", "s", "n"],
            default="f",
        )

        if mode == "f":
            proxy_path = Prompt.ask("Path to proxy file", default=_PROXY_FILE_DISPLAY)
            proxies = load_lines(_resolve_input_path(proxy_path))
            if not proxies:
                fail("No proxies found in that file.")
        elif mode == "p":
            console.print(f"\n[{C.PRIMARY}]Paste your proxies[/] [dim](one per line, empty line to finish)[/]")
            console.print(f"[{C.MUTED}]Format: login:pass@host:port[/]")
            lines_pasted = []
            while True:
                line = Prompt.ask("", default="")
                if not line.strip():
                    break
                lines_pasted.append(line.strip())
            if lines_pasted:
                ensure_file(DEFAULT_PROXY_FILE)
                Path(DEFAULT_PROXY_FILE).write_text("\n".join(lines_pasted), encoding="utf-8")
                proxies = lines_pasted
            else:
                fail("No proxies provided.")
        elif mode == "s":
            console.print()
            scraped_proxies = await _scrape_proxies()
            if scraped_proxies:
                proxies = scraped_proxies
                scraped = True

    if proxies:
        tag = f" [{C.MUTED}](free)[/]" if scraped else ""
        ok(f"{len(proxies)} proxies loaded{tag}")

        if len(proxies) > 1:
            remove_bad = Confirm.ask(
                "Auto-remove dead proxies?", default=True
            )
    else:
        warn_card(
            f"[{C.WARNING}]Running proxyless — expect heavy rate-limiting.[/]",
            f"[{C.MUTED}]Tip: close your Discord client to free up requests.[/]",
        )

    return proxies, remove_bad, scraped


# ---------------------------------------------------------------------------
# Step 2: Speed Test
# ---------------------------------------------------------------------------

async def _step_speed_test(proxies: list[str], config: Config) -> int:
    """Speed test scraped proxies and remove dead/slow ones."""
    from proxy import ProxyManager

    if not Confirm.ask(f"Speed test {len(proxies)} proxies?", default=True):
        ok("Skipping speed test")
        return 0

    pm = ProxyManager(proxies, remove_on_fail=True, scored=True)

    console.print()
    console.print(f"[{C.PRIMARY}]Testing {len(proxies)} proxies...[/]")
    console.print()

    def _on_progress(tested, total, working):
        pct = tested / max(total, 1) * 100
        console.print(f"\r  [{C.PRIMARY}]Testing[/] {tested}/{total} ({pct:.0f}%) - [{C.SUCCESS}]{working}[/] working", end="")

    results = await pm.speed_test(
        concurrency=100,
        timeout=5.0,
        on_progress=_on_progress,
    )
    console.print()

    working = await pm.apply_speed_results(results, remove_slow=True, max_latency_ms=10000)
    speed_test_result(results)

    if working == 0:
        console.print(f"[{C.WARNING}]No fast proxies found — using all scraped proxies[/]")
        working = len(proxies)

    # Update the proxy file with only working proxies
    working_proxies = [r[0] for r in results if r[2] and r[1] <= 10000]
    if not working_proxies:
        working_proxies = [r[0] for r in results if r[2]]
    if working_proxies:
        ensure_file(DEFAULT_PROXY_FILE)
        Path(DEFAULT_PROXY_FILE).write_text("\n".join(working_proxies), encoding="utf-8")
        ok(f"Saved {len(working_proxies)} fast proxies")

    return working


# ---------------------------------------------------------------------------
# Step 3: Usernames
# ---------------------------------------------------------------------------

def _step_usernames() -> list[str]:
    raw = Prompt.ask(
        f"[{C.PRIMARY}](f)ile[/] or [{C.PRIMARY}](g)enerate[/] usernames?",
        choices=["f", "g"],
        default="f",
    )
    mode = "generate" if raw == "g" else "file"
    usernames: list[str] = []

    if mode == "file":
        names_path = Prompt.ask("Path to username file", default=_NAMES_FILE_DISPLAY)
        usernames = load_lines(_resolve_input_path(names_path))
        if not usernames:
            fail("File is empty — switching to generate mode.")
            mode = "generate"
        else:
            ok(f"Loaded {len(usernames)} usernames")

    if mode == "generate":
        length = IntPrompt.ask("Username length", default=4, choices=["2", "3", "4", "5"])
        total = len(USERNAME_CHARS) ** length

        if length >= 5:
            ok(f"Generating 50000 random {length}-char usernames (of {total:,} possible)...")
            seen: set[str] = set()
            usernames = []
            while len(usernames) < 50000:
                cand = "".join(random.choices(USERNAME_CHARS, k=length))
                if cand not in seen and is_valid_username(cand):
                    seen.add(cand)
                    usernames.append(cand)
        else:
            combos = ["".join(c) for c in itertools.product(USERNAME_CHARS, repeat=length)]
            usernames = [c for c in combos if is_valid_username(c)]
            usernames = random.sample(usernames, min(50000, len(usernames)))

        ensure_file(DEFAULT_NAMES_FILE)
        Path(DEFAULT_NAMES_FILE).write_text("\n".join(usernames), encoding="utf-8")
        ok(f"Generated {len(usernames)} usernames (of {total:,} possible)")

    return usernames


# ---------------------------------------------------------------------------
# Step 4: Speed
# ---------------------------------------------------------------------------

def _step_speed(proxies: list[str], scraped: bool = False) -> tuple[int, int]:
    if not proxies:
        info("Proxyless mode — 1 worker with delay.")
        delay = IntPrompt.ask("Delay between requests (seconds)", default=5)
        return 1, delay

    if scraped:
        info("Free proxy mode — high concurrency, short timeout.")
        conc = IntPrompt.ask("Concurrent workers", default=100)
        if conc > MAX_CONCURRENCY:
            warn_card(f"Capped at {MAX_CONCURRENCY} — beyond this the program freezes.")
            conc = MAX_CONCURRENCY
        timeout = IntPrompt.ask("Request timeout (seconds)", default=5)
        return conc, timeout

    default_conc = min(MAX_CONCURRENCY, max(10, len(proxies) * 5))
    concurrency = IntPrompt.ask("Concurrent workers", default=default_conc)
    if concurrency > MAX_CONCURRENCY:
        warn_card(f"Capped at {MAX_CONCURRENCY} — beyond this the program freezes.")
        concurrency = MAX_CONCURRENCY
    timeout = IntPrompt.ask("Request timeout (seconds)", default=10)
    return concurrency, timeout


# ---------------------------------------------------------------------------
# Step 5: Webhook
# ---------------------------------------------------------------------------

def _step_webhook(config: Config) -> tuple[str | None, str | None]:
    saved_url = config.get("webhook")
    saved_msg = config.get("webhook_message", "**<name>** available | <t:time:R>")
    always = config.get("webhook_always", False)

    if always and saved_url:
        ok(f"Using saved webhook")
        return saved_url, saved_msg

    if saved_url and not always:
        if not Confirm.ask(
            f"Use webhook? [dim](saved from last session)[/]", default=True
        ):
            if Confirm.ask("Forget saved webhook?", default=False):
                config.set("webhook", "")
                config.set("webhook_message", "")
            return None, None
        webhook_url = saved_url
        webhook_msg = config.get("webhook_message", "**<name>** available | <t:time:R>")
    else:
        if not Confirm.ask("Send hits to a Discord webhook?", default=False):
            return None, None

        webhook_url = Prompt.ask("Webhook URL")
        if not webhook_url.strip():
            info("Empty URL — webhook disabled.")
            return None, None

        console.print(f"[{C.MUTED}]Hits are sent in batches to avoid rate-limits.[/]")
        webhook_msg = Prompt.ask(
            "Message template per hit [dim](<name> <time> <elapsed>)[/]",
            default="**<name>** available | <t:time:R>",
        )

    config.set("webhook", webhook_url)
    config.set("webhook_message", webhook_msg)

    if not always:
        if Confirm.ask("Always use this webhook? (skip asking next time)", default=True):
            config.set("webhook_always", True)

    return webhook_url, webhook_msg


# ---------------------------------------------------------------------------
# Proxy scraper (delegates to proxy.py centralized scraper)
# ---------------------------------------------------------------------------

async def _scrape_proxies() -> list[str]:
    from proxy import scrape_proxies

    def _on_progress(name, found, status):
        if status == "ok":
            console.print(f"  [{C.SUCCESS}]+[/] {name} {found} proxies")
        else:
            console.print(f"  [{C.DANGER}]x[/] {name} {status}")

    console.print(f"[{C.MUTED}]Scraping from public sources...[/]")
    all_proxies = await scrape_proxies(on_progress=_on_progress)

    if not all_proxies:
        fail("All sources failed — no proxies.")
        return []

    ok(f"{len(all_proxies)} unique proxies [{C.MUTED}](~2-5% usually work)[/]")
    return all_proxies
