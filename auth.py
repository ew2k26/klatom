#!/usr/bin/env python3
"""Klatom – Token validation with encrypted storage."""

from __future__ import annotations

import json
import platform
import time
from datetime import datetime, timedelta
from pathlib import Path

import aiohttp

from config import DATA_DIR, C
from crypto import (
    get_hwid, generate_token as _gen_token, hash_token,
    save_auth, load_auth, token_in_store, add_token_hash,
    save_session, load_session, ensure_creator, is_creator_token,
)

_AUTH_FILE = DATA_DIR / ".auth"
_SESSION_FILE = DATA_DIR / ".session"
_TOKENS_FILE = DATA_DIR / ".tokens"

TRIAL_HOURS = 24
TRIAL_SECONDS = TRIAL_HOURS * 3600


def generate_token() -> str:
    return _gen_token()


def add_approved_token(token: str) -> None:
    add_token_hash(_AUTH_FILE, token)
    if _TOKENS_FILE.exists():
        try:
            tokens = json.loads(_TOKENS_FILE.read_text(encoding="utf-8"))
        except Exception:
            tokens = []
    else:
        tokens = []
    if token.upper() not in [t.upper() for t in tokens]:
        tokens.append(token.upper())
        _TOKENS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _TOKENS_FILE.write_text(json.dumps(tokens, indent=2), encoding="utf-8")


def is_token_approved(token: str) -> bool:
    if token_in_store(token, _AUTH_FILE):
        return True
    if _TOKENS_FILE.exists():
        try:
            tokens = json.loads(_TOKENS_FILE.read_text(encoding="utf-8"))
            if token.upper() in [t.upper() for t in tokens]:
                return True
        except Exception:
            pass
    return False


def _activate_trial() -> None:
    save_session(_SESSION_FILE, time.time(), get_hwid())


def _is_trial_active() -> bool:
    data = load_session(_SESSION_FILE)
    if not data:
        return False
    start = data.get("ts", 0)
    hwid = data.get("th", "")
    if not start:
        return False
    if hwid and hwid != get_hwid():
        return False
    return (time.time() - start) < TRIAL_SECONDS


def _get_trial_remaining() -> float:
    data = load_session(_SESSION_FILE)
    if not data:
        return 0.0
    start = data.get("ts", 0)
    if not start:
        return 0.0
    return max(0.0, TRIAL_SECONDS - (time.time() - start))


def _format_time(seconds: float) -> str:
    if seconds <= 0:
        return "Expired"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}h {m}m {s}s"
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


def _get_token_type(token: str) -> str:
    t = token.upper()
    if t == "CREATOR":
        return "Creator"
    if t == "TRIAL":
        return "Free Trial"
    if t.startswith("KLATOM-"):
        return "Premium"
    return "Standard"


def show_session_info(token: str) -> None:
    from ui import console
    from rich.panel import Panel
    from rich.table import Table

    hwid = get_hwid()
    token_type = _get_token_type(token)

    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style=C.MUTED, width=16)
    t.add_column(style="white")

    t.add_row("Token Type", f"[{C.PRIMARY}]{token_type}[/]")
    t.add_row("HWID", f"[{C.MUTED}]{hwid}[/]")
    t.add_row("Machine", f"[{C.MUTED}]{platform.node()}[/]")

    if token_type == "Free Trial":
        remaining = _get_trial_remaining()
        color = C.SUCCESS if remaining > 3600 else C.WARNING
        t.add_row("Time Left", f"[{color}]{_format_time(remaining)}[/]")
        expires = datetime.now() + timedelta(seconds=remaining)
        t.add_row("Expires", f"[{C.MUTED}]{expires.strftime('%Y-%m-%d %H:%M')}[/]")

    console.print(Panel(
        t, title=f"[{C.PRIMARY}]Session Info[/]",
        title_align="left", border_style=C.PRIMARY, padding=(0, 1),
    ))


async def _log_to_webhook(token: str, action: str, webhook_url: str) -> None:
    embed = {
        "title": f"Klatom - {action}", "color": 0xA855F7,
        "fields": [
            {"name": "Token", "value": f"`{token}`", "inline": True},
            {"name": "Type", "value": f"`{_get_token_type(token)}`", "inline": True},
            {"name": "HWID", "value": f"`{get_hwid()}`", "inline": False},
            {"name": "Machine", "value": f"`{platform.node()}`", "inline": True},
            {"name": "Time", "value": f"`{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`", "inline": True},
        ],
    }
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.post(webhook_url, json={"content": "", "embeds": [embed]}):
                pass
    except Exception:
        pass


async def check_auth(webhook_url: str = "") -> tuple[bool, str]:
    from ui import console
    from rich.panel import Panel
    from rich.prompt import Prompt

    ensure_creator(_AUTH_FILE)

    data = load_auth(_AUTH_FILE)
    if data and hash_token("CREATOR") in data.get("t", []):
        show_session_info("CREATOR")
        return True, "CREATOR"

    if _is_trial_active():
        show_session_info("TRIAL")
        if webhook_url:
            await _log_to_webhook("TRIAL", "Trial Active", webhook_url)
        return True, "TRIAL"

    console.print()
    console.print(Panel(
        "[bold]Klatom License System[/]\n\n"
        "  [1] Enter token\n"
        "  [2] Start 24h free trial\n"
        "  [3] Exit",
        border_style=C.PRIMARY, title="Authentication", padding=(1, 2),
    ))

    choice = Prompt.ask(f"[{C.PRIMARY}]Choose[/]", choices=["1", "2", "3"], default="1").strip()

    if choice == "3":
        return False, ""
    if choice == "2":
        _activate_trial()
        console.print(f"[{C.SUCCESS}]Free trial activated — {TRIAL_HOURS}h started.[/]")
        show_session_info("TRIAL")
        if webhook_url:
            await _log_to_webhook("TRIAL", "Trial Started", webhook_url)
        return True, "TRIAL"

    token = Prompt.ask(f"[{C.PRIMARY}]Token[/]").strip()
    if not token:
        console.print(f"[{C.DANGER}]No token entered.[/]")
        return False, ""

    if webhook_url:
        await _log_to_webhook(token, "Token Attempt", webhook_url)

    if is_token_approved(token):
        console.print(f"[{C.SUCCESS}]Token approved.[/]")
        show_session_info(token)
        return True, token

    data = load_auth(_AUTH_FILE)
    if data and not data.get("t"):
        console.print(f"[{C.SUCCESS}]First run — you are the creator.[/]")
        add_approved_token("CREATOR")
        add_approved_token(token)
        show_session_info(token)
        return True, token

    console.print(f"[{C.DANGER}]Invalid token.[/]")
    return False, ""
