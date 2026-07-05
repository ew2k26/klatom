#!/usr/bin/env python3
"""Klatom v2.0.0 – Terminal UI."""

from __future__ import annotations

import os, sys

os.environ.setdefault("PYTHONUTF8", "1")
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from config import C, VERSION

console = Console()


def banner() -> Panel:
    inner = Text()
    inner.append("  ██╗  ██╗██╗      █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗", style=f"bold {C.PRIMARY}")
    inner.append("\n  ██║ ██╔╝██║     ██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║", style=f"bold {C.PRIMARY}")
    inner.append("\n  █████╔╝ ██║     ███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║", style=f"bold {C.PRIMARY}")
    inner.append("\n  ██╔═██╗ ██║     ██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║", style=f"bold {C.PRIMARY}")
    inner.append("\n  ██║  ██╗███████╗██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║", style=f"bold {C.PRIMARY}")
    inner.append("\n  ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝", style=f"bold {C.PRIMARY}")
    inner.append(f"\n\n         v{VERSION}", style=f"{C.MUTED}")
    inner.append("  Discord Username Checker", style=f"{C.MUTED}")
    return Panel(inner, box=box.DOUBLE, border_style=C.PRIMARY, padding=(0, 1))


def progress_steps(current: int, total: int = 4) -> str:
    steps = ["Proxies", "Usernames", "Speed", "Webhook"]
    parts = []
    for i, label in enumerate(steps):
        if i < current:
            parts.append(f"[{C.SUCCESS}]  {label}[/]")
        elif i == current:
            parts.append(f"[{C.PRIMARY}]  {label}[/]")
        else:
            parts.append(f"[{C.MUTED}]  {label}[/]")
    return " ".join(parts)


def section(title: str) -> None:
    console.print(f"\n[{C.PRIMARY}]── {title} ──[/]")


def ok(msg: str) -> None:
    console.print(f"  [{C.SUCCESS}]✓[/] {msg}")


def fail(msg: str) -> None:
    console.print(f"  [{C.DANGER}]✗[/] {msg}")


def info(msg: str) -> None:
    console.print(f"  [{C.PRIMARY}]ℹ[/] {msg}")


def warn_card(title: str, *lines: str) -> None:
    content = "\n".join(lines)
    console.print(Panel(content, title=title, border_style=C.WARNING, padding=(0, 1)))


def card(title: str, content: str) -> None:
    console.print(Panel(content, title=title, border_style=C.PRIMARY, padding=(0, 1)))


def config_summary(proxies: int, names: int, conc: int, timeout: int, webhook: str | None) -> None:
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style=C.MUTED, width=14)
    t.add_column(style="white")
    t.add_row("Proxies", f"[{C.PRIMARY}]{proxies}[/]")
    t.add_row("Usernames", f"[{C.PRIMARY}]{names}[/]")
    t.add_row("Concurrency", f"[{C.PRIMARY}]{conc}[/]")
    t.add_row("Timeout", f"[{C.PRIMARY}]{timeout}s[/]")
    t.add_row("Webhook", f"[{C.PRIMARY}]{webhook or 'Disabled'}[/]")
    console.print(Panel(t, title=f"[{C.PRIMARY}]Config[/]", title_align="left",
                        border_style=C.PRIMARY, padding=(0, 1)))


def final_summary(stats: dict, duration: float) -> None:
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style=C.MUTED, width=14)
    t.add_column(style="white")
    t.add_row("Total", f"[{C.PRIMARY}]{stats.get('requests', 0)}[/]")
    t.add_row("Available", f"[{C.SUCCESS}]{stats.get('works', 0)}[/]")
    t.add_row("Taken", f"[{C.DANGER}]{stats.get('taken', 0)}[/]")
    t.add_row("Rate Limited", f"[{C.WARNING}]{stats.get('ratelimited', 0)}[/]")
    t.add_row("Peak RPS", f"[{C.PRIMARY}]{stats.get('peak_rps', 0):.1f}[/]")
    t.add_row("Duration", f"[{C.PRIMARY}]{duration:.1f}s[/]")
    console.print(Panel(t, title=f"[{C.PRIMARY}]Results[/]", title_align="left",
                        border_style=C.PRIMARY, padding=(0, 1)))
