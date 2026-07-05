#!/usr/bin/env python3
"""Klatom – Standalone session info display."""

from __future__ import annotations

import hashlib
import json
import platform
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

if getattr(__import__("sys"), "frozen", False):
    _ROOT = Path(__import__("sys").executable).resolve().parent
else:
    _ROOT = Path(__file__).resolve().parent

_DATA = _ROOT / "data"
_AUTH_FILE = _DATA / ".auth"
_SESSION_FILE = _DATA / ".session"

TRIAL_SECONDS = 24 * 3600


def _hwid() -> str:
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
    if t.startswith("KLATOM-"):
        return "Premium"
    return "Standard"


def show() -> None:
    auth = _load(_AUTH_FILE)
    session = _load(_SESSION_FILE)
    hwid = _hwid()

    tokens = auth.get("tokens", [])
    trial_start = session.get("trial_start", 0)
    trial_hwid = session.get("trial_hwid", "")

    table = Table(box=None, show_header=False, padding=(0, 2))
    table.add_column(style="#98989D", width=16)
    table.add_column(style="white")

    if "CREATOR" in [t.upper() for t in tokens]:
        table.add_row("Token Type", "[#A855F7]Creator[/]")
    elif trial_start and (not trial_hwid or trial_hwid == hwid):
        remaining = max(0.0, TRIAL_SECONDS - (time.time() - trial_start))
        color = "#30D158" if remaining > 3600 else "#FF9F0A"
        table.add_row("Token Type", "[#A855F7]Free Trial[/]")
        table.add_row("Time Left", f"[{color}]{_fmt(remaining)}[/]")
        expires = datetime.now() + timedelta(seconds=remaining)
        table.add_row("Expires", f"[#98989D]{expires.strftime('%Y-%m-%d %H:%M')}[/]")
    elif tokens:
        last = tokens[-1]
        table.add_row("Token Type", f"[#A855F7]{_token_type(last)}[/]")
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
        title="[#A855F7]Klatom — Session Info[/]",
        title_align="left",
        border_style="#A855F7",
        padding=(0, 1),
    ))
    console.print()


if __name__ == "__main__":
    show()
