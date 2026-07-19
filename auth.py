#!/usr/bin/env python3
"""ew² v4.0 - Token validation with encrypted storage."""

from __future__ import annotations

import json
import platform
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

import aiohttp

from config import DATA_DIR, VERSION, C
from crypto import (
    get_hwid, generate_token as _gen_token, hash_token,
    save_auth, load_auth, token_in_store, add_token_hash,
    save_session, load_session,
    save_activation, load_activation, is_machine_activated,
    is_token_consumed, consume_token, remove_activation,
)

_AUTH_FILE = DATA_DIR / ".auth"
_SESSION_FILE = DATA_DIR / ".session"
_TOKENS_FILE = DATA_DIR / ".tokens"
_ACTIVATION_FILE = DATA_DIR / ".activation"

TRIAL_HOURS = 24
TRIAL_SECONDS = TRIAL_HOURS * 3600

# Backend API for token validation
_API_BASE = "https://ew2-payment.thiagoperres96.workers.dev"
_TOKEN_PATTERN = re.compile(r"^EW2-[A-F0-9]{8}-[A-F0-9]{8}-[A-F0-9]{8}$")


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


# ── One-time activation ──

def is_activated() -> bool:
    """Check if this machine has a valid activation."""
    return is_machine_activated(_ACTIVATION_FILE)


def activate_token(token: str) -> bool:
    """Activate a token for this machine. Returns True if successful.

    Flow:
    1. Validate token format (EW2- prefix)
    2. Check local .tokens pool first
    3. If not local, validate against backend API
    4. If valid, consume token and save activation
    """
    if not token or not token.strip():
        return False
    token = token.strip().upper()
    if not token.startswith("EW2-"):
        return False
    if is_token_consumed(_ACTIVATION_FILE, token):
        return False

    # Try local pool first
    available = _load_available_tokens()
    if token in [t.upper() for t in available]:
        consume_token(_ACTIVATION_FILE, token)
        _remove_token_from_pool(token)
        return True

    # Try online validation (purchased tokens)
    valid = False
    try:
        import asyncio
        import concurrent.futures

        async def _validate():
            return await _validate_token_online(token)

        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(lambda: asyncio.run(_validate()))
            valid, _ = future.result(timeout=15)
    except Exception:
        valid = False

    if valid:
        # Mark as activated locally
        consume_token(_ACTIVATION_FILE, token)
        # Also try to activate on backend (best effort)
        try:
            async def _activate():
                return await _activate_token_online(token)

            with concurrent.futures.ThreadPoolExecutor() as pool:
                pool.submit(lambda: asyncio.run(_activate())).result(timeout=10)
        except Exception:
            pass
        return True

    return False


def is_token_available(token: str) -> bool:
    """Check if a token is available for activation (exists in .tokens and not consumed)."""
    if not token or not token.strip():
        return False
    token = token.strip().upper()
    if not token.startswith("EW2-"):
        return False
    available = _load_available_tokens()
    if token not in [t.upper() for t in available]:
        return False
    if is_token_consumed(_ACTIVATION_FILE, token):
        return False
    return True


def _load_available_tokens() -> list[str]:
    """Load available tokens from .tokens file."""
    if not _TOKENS_FILE.exists():
        return []
    try:
        return json.loads(_TOKENS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _remove_token_from_pool(token: str) -> None:
    """Remove a token from the available pool (.tokens file)."""
    tokens = _load_available_tokens()
    tokens = [t for t in tokens if t.upper() != token.upper()]
    _TOKENS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _TOKENS_FILE.write_text(json.dumps(tokens, indent=2), encoding="utf-8")


async def _validate_token_online(token: str) -> tuple[bool, str]:
    """Validate token against the backend API. Returns (valid, error_msg)."""
    if not _TOKEN_PATTERN.match(token.upper()):
        return False, "Invalid token format"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{_API_BASE}/api/validate",
                json={"token": token, "hwid": get_hwid()},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                data = await resp.json()
                if resp.status == 200 and data.get("valid"):
                    return True, ""
                return False, data.get("error", "Validation failed")
    except Exception as e:
        return False, f"Network error: {e}"


async def _activate_token_online(token: str) -> tuple[bool, str]:
    """Activate token on the backend. Returns (success, error_msg)."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{_API_BASE}/api/activate",
                json={"token": token, "hwid": get_hwid()},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                data = await resp.json()
                if resp.status == 200 and data.get("success"):
                    return True, ""
                return False, data.get("error", "Activation failed")
    except Exception as e:
        return False, f"Network error: {e}"


def remove_activation() -> None:
    """Remove activation (for clear auth / testing)."""
    if _ACTIVATION_FILE.exists():
        _ACTIVATION_FILE.unlink()


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
    if t.startswith("EW2-"):
        return "Premium"
    return "Standard"


def show_session_info(token: str) -> None:
    from ui import console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    hwid = get_hwid()
    token_type = _get_token_type(token)

    inner = Text()
    inner.append("  ew²", style=f"bold {C.PRIMARY}")
    inner.append(f"  v{VERSION}", style=f"{C.MUTED}")

    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style=C.MUTED, width=16)
    t.add_column(style="white")

    t.add_row("Status", f"[{C.SUCCESS}]Authenticated[/]")
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
        t, title=inner,
        title_align="left", border_style=C.PRIMARY, padding=(0, 1),
    ))


async def _log_to_webhook(token: str, action: str, webhook_url: str) -> None:
    embed = {
        "title": f"ew² - {action}", "color": 0xA855F7,
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


def check_auth(webhook_url: str = "") -> tuple[bool, str]:
    """Check authentication. Returns (authenticated, token).

    Flow:
    1. Check if machine is activated (.activation file)
    2. Check if trial is active
    3. Check if CREATOR is already in .auth (legacy)
    4. Otherwise → prompt for token or trial
    """
    from ui import console
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.text import Text
    from rich import box

    # 1. Check activation (one-time token activation)
    if is_activated():
        data = load_activation(_ACTIVATION_FILE)
        if data:
            token_hash = data.get("token_hash", "")
            # Reconstruct display info
            console.print()
            console.print(f"[{C.SUCCESS}]Machine activated.[/]")
            show_session_info("ACTIVATED")
            return True, "ACTIVATED"

    # 2. Check for active trial
    if _is_trial_active():
        show_session_info("TRIAL")
        return True, "TRIAL"

    # 3. Check if CREATOR is already set up in .auth (legacy)
    data = load_auth(_AUTH_FILE)
    if data and hash_token("CREATOR") in data.get("t", []):
        show_session_info("CREATOR")
        return True, "CREATOR"

    # 4. Check if any tokens exist in .auth (legacy)
    has_tokens = data and len(data.get("t", [])) > 0

    console.print()

    if not has_tokens:
        console.print(Panel(
            Text.from_markup(
                f"[bold {C.PRIMARY}]Welcome to ew²[/]\n\n"
                f"  [{C.MUTED}]No license found. This appears to be the first run.[/]\n\n"
                f"  [{C.PRIMARY}]1[/]  Enter a license token\n"
                f"  [{C.PRIMARY}]2[/]  Start 24h free trial\n"
                f"  [{C.PRIMARY}]3[/]  Exit"
            ),
            border_style=C.PRIMARY,
            title=Text.from_markup(f"[{C.PRIMARY}]ew²[/] - License Required"),
            title_align="left",
            padding=(1, 2),
        ))
    else:
        console.print(Panel(
            Text.from_markup(
                f"[bold {C.PRIMARY}]ew² License[/]\n\n"
                f"  [{C.MUTED}]Enter your license token to continue.[/]\n\n"
                f"  [{C.PRIMARY}]1[/]  Enter token\n"
                f"  [{C.PRIMARY}]2[/]  Start 24h free trial\n"
                f"  [{C.PRIMARY}]3[/]  Exit"
            ),
            border_style=C.PRIMARY,
            title=Text.from_markup(f"[{C.PRIMARY}]ew²[/] - Authentication"),
            title_align="left",
            padding=(1, 2),
        ))

    choice = Prompt.ask(f"\n[{C.PRIMARY}]Choose[/]", choices=["1", "2", "3"], default="1").strip()

    if choice == "3":
        console.print(f"[{C.MUTED}]Goodbye.[/]")
        return False, ""

    if choice == "2":
        _activate_trial()
        console.print(f"\n[{C.SUCCESS}]Free trial activated - {TRIAL_HOURS}h started.[/]")
        show_session_info("TRIAL")
        return True, "TRIAL"

    # Choice 1: Enter token
    console.print()
    token = Prompt.ask(f"[{C.PRIMARY}]Enter your license token[/]").strip()
    if not token:
        console.print(f"[{C.DANGER}]No token entered.[/]")
        return False, ""

    # Try one-time activation first
    if activate_token(token):
        console.print(f"\n[{C.SUCCESS}]Token activated successfully.[/]")
        console.print(f"[{C.MUTED}]This machine is now licensed.[/]")
        show_session_info("ACTIVATED")
        return True, "ACTIVATED"

    # Legacy: check if token is already approved
    if is_token_approved(token):
        console.print(f"\n[{C.SUCCESS}]Token approved.[/]")
        show_session_info(token)
        return True, token

    console.print(f"\n[{C.DANGER}]Invalid, expired, or revoked token.[/]")
    console.print(f"[{C.MUTED}]Token not available. Check token or contact admin.[/]")
    return False, ""
