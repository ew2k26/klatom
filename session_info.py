#!/usr/bin/env python3
"""ew² – Standalone session info display."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from config import DATA_DIR

console = Console()

if getattr(sys, "frozen", False):
    _ROOT = Path(sys.executable).resolve().parent
else:
    _ROOT = Path(__file__).resolve().parent

_DATA = DATA_DIR
_AUTH_FILE = _DATA / ".auth"
_SESSION_FILE = _DATA / ".session"
_ACTIVATION_FILE = _DATA / ".activation"

TRIAL_SECONDS = 24 * 3600


def _hwid() -> str:
    try:
        from config import get_hwid_parts
        parts = get_hwid_parts()
        return hashlib.sha256("|".join(parts).encode()).hexdigest()[:24]
    except Exception:
        raw = f"{platform.node()}-{platform.machine()}-{uuid.getnode()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _fmt(seconds: float) -> str:
    if seconds <= 0:
        return "Expired"
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def _token_type(token: str) -> str:
    t = token.upper()
    if t == "CREATOR":
        return "Creator"
    if t == "TRIAL":
        return "Free Trial"
    if t.startswith("EW2-"):
        return "Premium"
    return "Standard"


def show() -> None:
    auth = _load(_AUTH_FILE)
    session = _load(_SESSION_FILE)
    activation = _load(_ACTIVATION_FILE)
    hwid = _hwid()

    tokens = auth.get("t", [])
    trial_start = session.get("ts", 0)
    trial_hwid = session.get("th", "")

    table = Table(box=None, show_header=False, padding=(0, 2))
    table.add_column(style="#98989D", width=16)
    table.add_column(style="white")

    # Check activation first
    if activation:
        act_hwid = activation.get("hwid", "")
        activated_at = activation.get("activated_at", 0)
        if act_hwid == hwid:
            table.add_row("Token Type", "[#C0C0C8]Premium (Activated)[/]")
            if activated_at:
                table.add_row("Activated", f"[#98989D]{datetime.fromtimestamp(activated_at).strftime('%Y-%m-%d %H:%M')}[/]")
        else:
            table.add_row("Token Type", "[#FF453A]Activation HWID mismatch[/]")
    elif "CREATOR" in [t.upper() for t in tokens]:
        table.add_row("Token Type", "[#C0C0C8]Creator[/]")
    elif trial_start and (not trial_hwid or trial_hwid == hwid):
        remaining = max(0.0, TRIAL_SECONDS - (time.time() - trial_start))
        color = "#30D158" if remaining > 3600 else "#FF9F0A"
        table.add_row("Token Type", "[#C0C0C8]Free Trial[/]")
        table.add_row("Time Left", f"[{color}]{_fmt(remaining)}[/]")
        expires = datetime.now() + timedelta(seconds=remaining)
        table.add_row("Expires", f"[#98989D]{expires.strftime('%Y-%m-%d %H:%M')}[/]")
    elif tokens:
        last = tokens[-1]
        table.add_row("Token Type", f"[#C0C0C8]{_token_type(last)}[/]")
        table.add_row("Token", f"[#98989D]{last[:20]}...[/]")
    else:
        table.add_row("Token Type", "[#FF453A]None[/]")
        table.add_row("Status", "[#FF453A]No token or trial active[/]")

    table.add_row("HWID", f"[#98989D]{hwid}[/]")
    table.add_row("Machine", f"[#98989D]{platform.node()}[/]")
    table.add_row("Tokens", f"[#98989D]{len(tokens)} loaded[/]")

    console.print()
    console.print(Panel(
        table,
        title="[#C0C0C8]ew² — Session Info[/]",
        title_align="left",
        border_style="#3A3A3A",
        padding=(0, 1),
    ))
    console.print()


if __name__ == "__main__":
    show()
