#!/usr/bin/env python3
"""KLATOM v3.3 - Terminal UI."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from config import C, VERSION


console = Console()


def banner() -> Panel:
    inner = Text()
    inner.append("  KL", style=f"bold {C.PRIMARY}")
    inner.append("ATOM", style=f"bold white")
    inner.append(f"  v{VERSION}", style=f"{C.MUTED}")
    return Panel(
        inner,
        box=box.DOUBLE,
        border_style=C.PRIMARY,
        padding=(1, 2),
    )


def progress_steps(current: int, total: int = 5) -> str:
    steps = ["Proxies", "Speed", "Usernames", "Speed", "Webhook"]
    parts: list[str] = []
    for i, label in enumerate(steps):
        if i < current:
            parts.append(f"[{C.SUCCESS}]{label}[/]")
        elif i == current:
            parts.append(f"[{C.PRIMARY}][{label}][/]")
        else:
            parts.append(f"[{C.MUTED}]{label}[/]")
    return "  ".join(parts)


def section(title: str) -> None:
    console.print()
    console.print(Text(title, style=f"bold {C.PRIMARY}"))
    console.print("─" * 50, style=C.BORDER)


def card(title: str | None, *lines: str, border: str = C.PRIMARY) -> None:
    body = "\n".join(lines) if lines else ""
    console.print(Panel(
        body,
        title=title,
        title_align="left",
        box=box.ROUNDED,
        border_style=border,
        padding=(1, 2),
    ))


def info_card(*lines: str) -> None:
    card(None, *lines, border=C.MUTED)


def warn_card(*lines: str) -> None:
    card(None, *lines, border=C.WARNING)


def config_summary(
    proxy_count: int,
    scraped: bool,
    remove_bad: bool,
    username_count: int,
    concurrency: int,
    timeout: int,
    webhook: bool,
    working_proxies: int = 0,
) -> None:
    console.print()
    t = Table(box=box.ROUNDED, border_style=C.BORDER, show_header=False, padding=(0, 2))
    t.add_column(style=C.MUTED, width=16)
    t.add_column(style="white")

    tag = f" [{C.MUTED}](free)[/]" if scraped else ""
    t.add_row("Proxies", f"[{C.PRIMARY}]{proxy_count}[/] loaded{tag}")
    if working_proxies > 0 and scraped:
        t.add_row("Working", f"[{C.SUCCESS}]{working_proxies}[/] alive")
    if proxy_count > 1 and not scraped:
        t.add_row("Auto-remove", "Yes" if remove_bad else "No")
    t.add_row("Usernames", str(username_count))
    t.add_row("Workers", str(concurrency))
    t.add_row("Timeout", f"{timeout}s")
    t.add_row("Webhook", f"[{C.SUCCESS}]on[/]" if webhook else f"[{C.MUTED}]off[/]")
    console.print(Panel(t, title="[bold]Config Summary[/]", title_align="left", box=box.ROUNDED, border_style=C.PRIMARY))


def speed_test_progress(tested: int, total: int, working: int) -> None:
    pct = tested / max(total, 1) * 100
    console.print(f"\r  [{C.PRIMARY}]Testing proxies[/] {tested}/{total} ({pct:.0f}%) - [{C.SUCCESS}]{working}[/] working", end="")


def speed_test_result(results: list[tuple[str, float, bool]]) -> None:
    working = [r for r in results if r[2]]
    dead = [r for r in results if not r[2]]

    t = Table(box=box.ROUNDED, border_style=C.BORDER, show_header=False, padding=(0, 2))
    t.add_column(style=C.MUTED, width=16)
    t.add_column(style="white")

    t.add_row("Total tested", str(len(results)))
    t.add_row("Working", f"[{C.SUCCESS}]{len(working)}[/]")
    t.add_row("Dead/Slow", f"[{C.DANGER}]{len(dead)}[/]")

    if working:
        latencies = [r[1] for r in working]
        avg = sum(latencies) / len(latencies)
        fast = [r for r in working if r[1] < 1000]
        medium = [r for r in working if 1000 <= r[1] < 2000]
        slow = [r for r in working if r[1] >= 2000]
        t.add_row("Avg latency", f"{avg:.0f}ms")
        t.add_row("Fast (<1s)", f"[{C.SUCCESS}]{len(fast)}[/]")
        t.add_row("Medium (1-2s)", f"[{C.WARNING}]{len(medium)}[/]")
        t.add_row("Slow (>2s)", f"[{C.DANGER}]{len(slow)}[/]")

        top5 = sorted(working, key=lambda x: x[1])[:5]
        if top5:
            top_str = "  ".join(f"{r[0].split('://')[-1][:20]} [{C.SUCCESS}]{r[1]:.0f}ms[/]" for r in top5)
            t.add_row("Fastest", top_str)

    console.print()
    console.print(Panel(t, title="[bold]Speed Test Results[/]", title_align="left", box=box.ROUNDED, border_style=C.SUCCESS))


def live_card(
    done: int,
    total: int,
    works: int,
    taken: int,
    requests: int,
    ratelimited: int,
    circuit_opens: int,
    rps: float,
    elapsed: float,
    proxy_alive: int,
    checks_rps: float = 0.0,
    paused: bool = False,
    errors: int = 0,
    avg_latency: float = 0.0,
    recent: list[str] | None = None,
    feed: list[str] | None = None,
) -> Panel:

    pct = done / max(total, 1) * 100

    inner = Table(box=None, show_header=False, padding=(0, 1), expand=True)
    inner.add_column(style=C.MUTED, width=14, no_wrap=True)
    inner.add_column(style="white")
    inner.add_column(style=C.MUTED, width=14, no_wrap=True)
    inner.add_column(style="white")

    inner.add_row(
        "Available", f"[{C.SUCCESS}]{works}[/]",
        "Taken", f"[{C.DANGER}]{taken}[/]",
    )
    inner.add_row(
        "Req/s", f"[{C.PRIMARY}]{rps:.0f}[/]",
        "Requests", str(requests),
    )

    if errors > 0:
        inner.add_row(
            f"[{C.DANGER}]Errors[/]", f"[{C.DANGER}]{errors}[/]",
            "Elapsed", f"{elapsed:.0f}s",
        )
    elif ratelimited > 0:
        inner.add_row(
            f"[{C.WARNING}]Rate limited[/]", f"[{C.WARNING}]{ratelimited}[/]",
            "Elapsed", f"{elapsed:.0f}s",
        )
    else:
        inner.add_row(
            "Progress", f"{done}/{total} ({pct:.0f}%)",
            "Elapsed", f"{elapsed:.0f}s",
        )

    if circuit_opens > 0 or paused:
        inner.add_row(
            f"[{C.WARNING}]Circuit breaks[/]", f"[{C.WARNING}]{circuit_opens}[/]",
            "Proxies", f"{proxy_alive} alive",
        )
    elif avg_latency > 0:
        inner.add_row(
            "Proxies", f"{proxy_alive} alive",
            "Avg latency", f"{avg_latency:.0f}ms",
        )
    else:
        inner.add_row(
            "Proxies", f"{proxy_alive} alive",
            "Workers", "active",
        )

    content = Table(box=None, show_header=False, padding=(0, 0), expand=True)
    content.add_row(inner)

    if ratelimited > 0 and (done == 0 or ratelimited > done * 2):
        content.add_section()
        content.add_row(Text(
            f"[!] Discord is rate-limiting - {ratelimited} requests blocked.",
            style=C.WARNING,
        ))

    if paused:
        content.add_section()
        content.add_row(Text(
            f"[!] Circuit breaker active - workers paused.",
            style=C.WARNING,
        ))

    if recent:
        content.add_section()
        recent_str = "  ".join(f"[{C.SUCCESS}]{n}[/]" for n in recent[-6:])
        content.add_row(Text("Recent  ", style=C.MUTED) + Text.from_markup(recent_str))

    if feed:
        content.add_section()
        display_feed = feed[-12:]
        feed_str = "  ".join(display_feed)
        content.add_row(Text.from_markup(feed_str))

    status = f"waiting" if (ratelimited > 0 and done == 0) else f"{done}/{total} ({pct:.0f}%)"
    return Panel(
        content,
        title=f"[{C.PRIMARY}]KLATOM[/] . {status} . [dim]{elapsed:.0f}s[/]",
        title_align="left",
        box=box.ROUNDED,
        border_style=C.PRIMARY if not paused else C.WARNING,
        padding=(1, 2),
    )


def final_summary(
    requests: int,
    works: int,
    taken: int,
    ratelimited: int,
    circuit_opens: int,
    elapsed: float,
    peak_rps: float = 0.0,
    best_streak: int = 0,
    errors: int = 0,
) -> None:
    console.print()

    avg_rps = requests / max(elapsed, 0.1)

    t = Table(box=box.ROUNDED, border_style=C.BORDER, show_header=False, padding=(0, 2))
    t.add_column(style=C.MUTED, width=16)
    t.add_column(style="white")
    t.add_row("Available", f"[{C.SUCCESS} bold]{works}[/]")
    t.add_row("Taken", f"[{C.DANGER} bold]{taken}[/]")
    t.add_row("Requests", str(requests))
    if ratelimited > 0:
        t.add_row("Rate limited", f"[{C.WARNING}]{ratelimited}[/]")
    if errors > 0:
        t.add_row("Errors", f"[{C.DANGER}]{errors}[/]")
    if circuit_opens > 0:
        t.add_row("Circuit breaks", str(circuit_opens))
    t.add_row("Elapsed", f"{elapsed:.0f}s")
    t.add_row("Avg req/s", f"{avg_rps:.1f}")
    if peak_rps > 0:
        t.add_row("Peak req/s", f"[{C.PRIMARY}]{peak_rps:.0f}[/]")
    if best_streak > 1:
        t.add_row("Best streak", f"[{C.SUCCESS}]{best_streak}[/] hits")
    if works > 0:
        t.add_row("Saved to", "results/hits.txt")

    console.print(Panel(
        t,
        title=f"[{C.SUCCESS}]Done[/] . {elapsed:.0f}s",
        title_align="left",
        box=box.ROUNDED,
        border_style=C.SUCCESS,
    ))


def ok(msg: str) -> None:
    console.print(f"  [{C.SUCCESS}]+[/] {msg}")

def fail(msg: str) -> None:
    console.print(f"  [{C.DANGER}]x[/] {msg}")

def info(msg: str) -> None:
    console.print(f"  [{C.MUTED}]~[/] {msg}")
