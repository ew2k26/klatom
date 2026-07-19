#!/usr/bin/env python3
"""ew² v4.0 - Mod Panel GUI (PySide6)."""

from __future__ import annotations

import asyncio
import hashlib
import json
import platform
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

try:
    from PySide6.QtCore import Qt, QTimer, Signal, QThread, QObject, QSize
    from PySide6.QtGui import QFont, QColor
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QStackedWidget, QLabel, QLineEdit, QPushButton, QCheckBox,
        QTextEdit, QFrame, QTabWidget, QGridLayout, QFileDialog,
        QMessageBox, QPlainTextEdit,
    )
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

from config import DATA_DIR, VERSION

if HAS_PYSIDE6:
    BG = "#050508"
    BG2 = "#0A0A0F"
    BG3 = "#101018"
    BORDER = "#1A1A24"
    BORDER2 = "#242430"
    TXT = "#E8E8ED"
    TXT2 = "#707080"
    MUTED = "#555560"
    PRIMARY = "#3A3A3A"
    PRIMARY_D = "#2A2A2A"
    PRIMARY_L = "#505050"
    SUCCESS = "#28C840"
    DANGER = "#E03030"
    WARNING = "#E08800"

    _mono = "Consolas" if sys.platform == "win32" else "DejaVu Sans Mono"
    _sans = "Segoe UI" if sys.platform == "win32" else "DejaVu Sans"

    STYLESHEET = f"""
    * {{ font-family: "{_sans}"; font-size: 13px; }}
    QWidget {{ background-color: {BG}; color: {TXT}; border: none; }}
    QMainWindow {{ background-color: {BG}; }}
    QLabel {{ background: transparent; padding: 0; }}
    QLineEdit {{
        background-color: {BG3}; color: {TXT}; border: 1px solid {BORDER};
        border-radius: 6px; padding: 10px 14px; font-size: 14px;
    }}
    QLineEdit:focus {{ border: 1px solid {PRIMARY_L}; }}
    QPushButton {{
        background-color: {PRIMARY}; color: #fff; border: none;
        border-radius: 6px; padding: 10px 24px; font-weight: bold;
        font-size: 13px; min-height: 20px;
    }}
    QPushButton:hover {{ background-color: {PRIMARY_L}; }}
    QPushButton:pressed {{ background-color: {PRIMARY_D}; }}
    QPushButton:disabled {{ background-color: {BG3}; color: {MUTED}; }}
    QPushButton#accent {{ background-color: {SUCCESS}; color: #fff; }}
    QPushButton#accent:hover {{ background-color: #30D848; }}
    QPushButton#danger {{ background-color: {DANGER}; color: #fff; }}
    QPushButton#danger:hover {{ background-color: #F04040; }}
    QPushButton#ghost {{
        background-color: transparent; color: {TXT2};
        border: 1px solid {BORDER};
    }}
    QPushButton#ghost:hover {{ background-color: {BG3}; color: {TXT}; border-color: {PRIMARY_L}; }}
    QCheckBox {{ spacing: 8px; color: {TXT2}; font-size: 12px; }}
    QCheckBox::indicator {{
        width: 18px; height: 18px; border: 2px solid {BORDER2};
        border-radius: 4px; background: {BG3};
    }}
    QCheckBox::indicator:checked {{ background: {PRIMARY_L}; border: 2px solid {PRIMARY_L}; }}
    QProgressBar {{
        background-color: {BG3}; border: none; border-radius: 4px;
        height: 8px; text-align: center; color: transparent;
    }}
    QProgressBar::chunk {{ background-color: {PRIMARY_L}; border-radius: 4px; }}
    QTabWidget::pane {{ border: 1px solid {BORDER}; background: {BG}; top: -1px; }}
    QTabBar::tab {{
        background: {BG2}; color: {MUTED}; padding: 8px 20px;
        border: 1px solid {BORDER}; border-bottom: none;
        border-top-left-radius: 6px; border-top-right-radius: 6px;
        margin-right: 2px; font-size: 12px;
    }}
    QTabBar::tab:selected {{ color: {TXT}; background: {BG}; border-color: {BORDER2}; }}
    QTabBar::tab:hover {{ color: {TXT2}; background: {BG3}; }}
    QFrame[frameShape="4"] {{ background: {BORDER}; max-height: 1px; }}
    QPlainTextEdit {{
        background-color: {BG3}; color: {TXT2}; border: 1px solid {BORDER};
        border-radius: 6px; padding: 8px; font-family: "{_mono}"; font-size: 12px;
    }}
    QPlainTextEdit:focus {{ border: 1px solid {PRIMARY_L}; }}
    QToolTip {{
        background: {BG3}; color: {TXT}; border: 1px solid {BORDER2};
        padding: 6px; border-radius: 4px; font-size: 12px;
    }}
    """

AUTH_FILE = DATA_DIR / ".auth"
SESSION_FILE = DATA_DIR / ".session"
TOKENS_FILE = DATA_DIR / ".tokens"
ACTIVATION_FILE = DATA_DIR / ".activation"


def _hwid() -> str:
    try:
        from config import get_hwid_parts
        parts = get_hwid_parts()
        return hashlib.sha256("|".join(parts).encode()).hexdigest()[:24]
    except Exception:
        return "unknown"


class ModApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"ew\u00B2 - Mod Panel v{VERSION}")
        self.setMinimumSize(720, 560)
        self.resize(780, 600)
        self.setStyleSheet(STYLESHEET)
        self._set_icon()
        self._build_ui()
        self._show_session()

    def _set_icon(self):
        """Load and set the app icon from ew2.ico."""
        try:
            candidates = []
            if getattr(sys, 'frozen', False):
                base = Path(sys.executable).resolve().parent
                candidates.append(base / "ew2.ico")
                candidates.append(base / "ew2_icon.png")
                meipass = getattr(sys, '_MEIPASS', None)
                if meipass:
                    candidates.append(Path(meipass) / "ew2.ico")
                    candidates.append(Path(meipass) / "ew2_icon.png")
            else:
                base = Path(__file__).resolve().parent
                candidates.append(base / "ew2.ico")
                candidates.append(base / "ew2_icon.png")
            for icon_path in candidates:
                if icon_path.exists():
                    from PySide6.QtGui import QIcon
                    icon = QIcon(str(icon_path))
                    self.setWindowIcon(icon)
                    QApplication.instance().setWindowIcon(icon)
                    return
        except Exception:
            pass

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        lay = QVBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._make_header())

        body = QWidget()
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(0)

        sidebar = QFrame()
        sidebar.setFixedWidth(160)
        sidebar.setStyleSheet(
            f"background: {BG2}; border-right: 1px solid {BORDER};"
        )
        sb_lay = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(8, 12, 8, 12)
        sb_lay.setSpacing(4)

        self._nav_btns = []
        for label, cmd in [
            ("Session", self._show_session),
            ("Tokens", self._show_tokens),
            ("Generate", self._show_generate),
            ("Speed Test", self._show_speed_test),
            ("Hits", self._show_hits),
            ("Clear Auth", self._show_clear_auth),
        ]:
            btn = QPushButton(label)
            btn.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {TXT2}; "
                f"border: none; border-radius: 6px; padding: 10px 14px; "
                f"text-align: left; font-size: 13px; font-weight: normal; }}"
                f"QPushButton:hover {{ background: {BG3}; color: {TXT}; }}"
                f"QPushButton:checked {{ background: {PRIMARY}; color: #fff; font-weight: bold; }}"
            )
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, c=cmd, b=btn: self._nav_click(c, b))
            sb_lay.addWidget(btn)
            self._nav_btns.append(btn)
        sb_lay.addStretch()

        body_lay.addWidget(sidebar)

        content = QWidget()
        content_lay = QVBoxLayout(content)
        content_lay.setContentsMargins(0, 0, 0, 0)
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        content_lay.addWidget(self._tabs)
        body_lay.addWidget(content, 1)

        lay.addWidget(body, 1)

    def _nav_click(self, cmd, btn):
        for b in self._nav_btns:
            b.setChecked(False)
        btn.setChecked(True)
        cmd()

    def _make_header(self):
        h = QFrame()
        h.setFixedHeight(56)
        h.setStyleSheet(f"background: {BG2}; border-bottom: 1px solid {BORDER};")
        hl = QHBoxLayout(h)
        hl.setContentsMargins(24, 0, 24, 0)
        t = QLabel()
        t.setText(
            f'<span style="color:{PRIMARY};font-size:22px;font-weight:bold">ew</span>'
            f'<span style="color:{TXT};font-size:22px;font-weight:bold">\u00B2</span>'
            f'<span style="color:{WARNING};font-size:13px;font-weight:bold;margin-left:12px">MOD PANEL</span>'
            f'<span style="color:{MUTED};font-size:13px;margin-left:8px">v{VERSION}</span>'
        )
        hl.addWidget(t)
        hl.addStretch()
        admin = QLabel("Admin")
        admin.setStyleSheet(
            f"color: {WARNING}; background: {BG3}; padding: 4px 12px; border-radius: 4px; font-size: 11px;"
        )
        hl.addWidget(admin)
        return h

    def _make_button(self, text, bg=PRIMARY, fg="#fff", hover=None, command=None):
        btn = QPushButton(text)
        btn.setStyleSheet(
            f"background-color: {bg}; color: {fg}; border-radius: 6px; "
            f"padding: 8px 18px; font-weight: bold; font-size: 12px;"
        )
        if hover:
            btn.setStyleSheet(btn.styleSheet() + f"QPushButton:hover{{ background-color: {hover}; }}")
        if command:
            btn.clicked.connect(command)
        return btn

    def _make_info_row(self, label, value, color=MUTED):
        row = QHBoxLayout()
        ll = QLabel(label)
        ll.setFixedWidth(140)
        ll.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        row.addWidget(ll)
        vl = QLabel(str(value))
        vl.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 12px;")
        row.addWidget(vl)
        row.addStretch()
        return row

    def _show_session(self):
        self._tabs.clear()
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(30, 20, 30, 20)

        t = QLabel("Session Info")
        t.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {TXT};")
        lay.addWidget(t)
        lay.addSpacing(16)

        card = QFrame()
        card.setStyleSheet(f"background: {BG2}; border: 1px solid {BORDER}; border-radius: 8px;")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.setSpacing(10)

        hwid = _hwid()
        cl.addLayout(self._make_info_row("HWID", hwid))
        cl.addLayout(self._make_info_row("Machine", platform.node()))

        # Check activation status
        activation_data = None
        if ACTIVATION_FILE.exists():
            try:
                from crypto import load_activation
                activation_data = load_activation(ACTIVATION_FILE)
            except Exception:
                pass
        if activation_data:
            token_hash = activation_data.get("token_hash", "")
            activated_at = activation_data.get("activated_at", 0)
            act_hwid = activation_data.get("hwid", "")
            status = "ACTIVE" if act_hwid == hwid else "HWID MISMATCH"
            color = SUCCESS if status == "ACTIVE" else DANGER
            cl.addLayout(self._make_info_row("License Status", status, color))
            cl.addLayout(self._make_info_row("Activated", datetime.fromtimestamp(activated_at).strftime("%Y-%m-%d %H:%M") if activated_at else "Unknown"))
        else:
            cl.addLayout(self._make_info_row("License Status", "Not activated", DANGER))

        auth_data = None
        if AUTH_FILE.exists():
            try:
                from crypto import load_auth
                auth_data = load_auth(AUTH_FILE)
            except Exception:
                pass
        if auth_data:
            th = auth_data.get("t", [])
            cl.addLayout(self._make_info_row("Stored Tokens", f"{len(th)} (hashed)", PRIMARY))
        else:
            cl.addLayout(self._make_info_row("Auth File", "Not found", DANGER))

        session_data = None
        if SESSION_FILE.exists():
            try:
                from crypto import load_session
                session_data = load_session(SESSION_FILE)
            except Exception:
                pass
        if session_data:
            start = session_data.get("ts", 0)
            if start:
                remaining = max(0, 86400 - (time.time() - start))
                if remaining > 0:
                    h = int(remaining // 3600)
                    m = int((remaining % 3600) // 60)
                    s = int(remaining % 60)
                    color = SUCCESS if remaining > 3600 else WARNING
                    cl.addLayout(self._make_info_row("Trial Status", "ACTIVE", color))
                    cl.addLayout(self._make_info_row("Time Left", f"{h}h {m}m {s}s", color))
                    expires = datetime.now() + timedelta(seconds=remaining)
                    cl.addLayout(self._make_info_row("Expires", expires.strftime("%Y-%m-%d %H:%M")))
                else:
                    cl.addLayout(self._make_info_row("Trial Status", "EXPIRED", DANGER))
            else:
                cl.addLayout(self._make_info_row("Trial Status", "Not started", DANGER))
        else:
            cl.addLayout(self._make_info_row("Trial Status", "No session", DANGER))

        tokens_count = 0
        if TOKENS_FILE.exists():
            try:
                tokens = json.loads(TOKENS_FILE.read_text(encoding="utf-8"))
                tokens_count = len(tokens)
            except Exception:
                pass
        cl.addLayout(self._make_info_row("Tokens File", f"{tokens_count} tokens", PRIMARY))

        hits_count = 0
        hits_file = DATA_DIR / "hits.txt"
        if hits_file.exists():
            hits_count = len([l for l in hits_file.read_text(encoding="utf-8").splitlines() if l.strip()])
        cl.addLayout(self._make_info_row("Hits Found", str(hits_count), SUCCESS))

        lay.addWidget(card)
        lay.addStretch()
        self._tabs.addTab(page, "Session")

    def _show_tokens(self):
        self._tabs.clear()
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(30, 20, 30, 20)

        t = QLabel("Token Management")
        t.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {TXT};")
        lay.addWidget(t)
        lay.addSpacing(16)

        if not TOKENS_FILE.exists():
            lay.addWidget(QLabel("No tokens file found."))
            lay.addStretch()
            self._tabs.addTab(page, "Tokens")
            return

        try:
            tokens = json.loads(TOKENS_FILE.read_text(encoding="utf-8"))
        except Exception:
            lay.addWidget(QLabel("Invalid tokens file."))
            lay.addStretch()
            self._tabs.addTab(page, "Tokens")
            return

        if not tokens:
            lay.addWidget(QLabel("No tokens stored."))
            lay.addStretch()
            self._tabs.addTab(page, "Tokens")
            return

        lbl = QLabel(f"Stored Tokens ({len(tokens)}):")
        lbl.setStyleSheet(f"color: {PRIMARY}; font-weight: bold;")
        lay.addWidget(lbl)
        lay.addSpacing(8)

        card = QFrame()
        card.setStyleSheet(f"background: {BG2}; border: 1px solid {BORDER}; border-radius: 8px;")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 12, 16, 12)
        cl.setSpacing(4)
        for i, tok in enumerate(tokens, 1):
            row = QHBoxLayout()
            num = QLabel(f"{i}.")
            num.setFixedWidth(30)
            num.setStyleSheet(f"color: {MUTED}; font-family: '{_mono}'; font-size: 12px;")
            row.addWidget(num)
            vl = QLabel(tok)
            vl.setStyleSheet(f"color: {PRIMARY}; font-family: '{_mono}'; font-size: 12px;")
            row.addWidget(vl)
            row.addStretch()
            cl.addLayout(row)
        lay.addWidget(card, 1)

        revoke_row = QHBoxLayout()
        revoke_row.addWidget(QLabel("Revoke:"))
        self._revoke_input = QLineEdit()
        self._revoke_input.setPlaceholderText("Token number or full token")
        self._revoke_input.setMaximumWidth(300)
        revoke_row.addWidget(self._revoke_input)
        revoke_btn = self._make_button("Revoke", DANGER, "#fff", "#F04040", self._do_revoke)
        revoke_row.addWidget(revoke_btn)
        revoke_row.addStretch()
        lay.addLayout(revoke_row)

        self._tabs.addTab(page, "Tokens")

    def _do_revoke(self):
        raw = self._revoke_input.text().strip()
        if not raw:
            QMessageBox.warning(self, "ew\u00B2", "Enter a token number to revoke.")
            return
        try:
            tokens = json.loads(TOKENS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(tokens):
                tokens.pop(idx)
                TOKENS_FILE.write_text(json.dumps(tokens, indent=2), encoding="utf-8")
                QMessageBox.information(self, "ew\u00B2", f"Token revoked. Remaining: {len(tokens)}")
                self._show_tokens()
                return
        except ValueError:
            if raw in tokens:
                tokens.remove(raw)
                TOKENS_FILE.write_text(json.dumps(tokens, indent=2), encoding="utf-8")
                QMessageBox.information(self, "ew\u00B2", f"Token revoked. Remaining: {len(tokens)}")
                self._show_tokens()
                return
        QMessageBox.warning(self, "ew\u00B2", "Token not found.")

    def _show_generate(self):
        self._tabs.clear()
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(30, 20, 30, 20)

        t = QLabel("Generate Tokens")
        t.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {TXT};")
        lay.addWidget(t)
        lay.addSpacing(16)

        row = QHBoxLayout()
        row.addWidget(QLabel("Number of tokens:"))
        self._gen_count = QLineEdit("1")
        self._gen_count.setMaximumWidth(80)
        row.addWidget(self._gen_count)
        row.addStretch()
        lay.addLayout(row)
        lay.addSpacing(12)

        self._gen_display = QPlainTextEdit()
        self._gen_display.setReadOnly(True)
        lay.addWidget(self._gen_display, 1)

        btn = self._make_button("Generate", PRIMARY, "#fff", command=self._do_generate)
        lay.addWidget(btn, 0, Qt.AlignLeft)

        self._tabs.addTab(page, "Generate")

    def _do_generate(self):
        try:
            count = int(self._gen_count.text())
        except ValueError:
            count = 1
        count = max(1, count)

        from crypto import generate_token as _gen
        existing = []
        if TOKENS_FILE.exists():
            try:
                existing = json.loads(TOKENS_FILE.read_text(encoding="utf-8"))
            except Exception:
                existing = []

        new_tokens = []
        for _ in range(count):
            tok = _gen()
            new_tokens.append(tok)
            existing.append(tok)

        TOKENS_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKENS_FILE.write_text(json.dumps(existing, indent=2), encoding="utf-8")

        self._gen_display.setPlainText(
            f"Generated {count} token(s):\n\n" +
            "\n".join(f"  {t}" for t in new_tokens) +
            f"\n\nTotal: {len(existing)}"
        )

    def _show_speed_test(self):
        self._tabs.clear()
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(30, 20, 30, 20)

        t = QLabel("Proxy Speed Test")
        t.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {TXT};")
        lay.addWidget(t)
        lay.addSpacing(4)
        sub = QLabel("Enter proxies (one per line) or load from file")
        sub.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        lay.addWidget(sub)
        lay.addSpacing(12)

        btn_row = QHBoxLayout()
        for label, cmd in [
            ("Load File", self._speed_load_file),
            ("Load Cache", self._speed_load_cache),
            ("Scrape", self._speed_scrape),
            ("Clear", self._speed_clear),
        ]:
            b = self._make_button(label, BG3 if label != "Scrape" else PRIMARY, "#fff" if label == "Scrape" else TXT, BORDER, cmd)
            btn_row.addWidget(b)
        btn_row.addStretch()
        lay.addLayout(btn_row)
        lay.addSpacing(8)

        self._speed_text = QPlainTextEdit()
        self._speed_text.setPlaceholderText("login:pass@host:port")
        self._speed_text.setMaximumHeight(140)
        lay.addWidget(self._speed_text)

        self._speed_count = QLabel("0 proxies")
        self._speed_count.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        lay.addWidget(self._speed_count)
        lay.addSpacing(4)

        self._speed_bar = QProgressBar()
        lay.addWidget(self._speed_bar)
        lay.addSpacing(4)

        self._speed_lbl = QLabel("Ready")
        self._speed_lbl.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        lay.addWidget(self._speed_lbl)

        self._speed_results = QPlainTextEdit()
        self._speed_results.setReadOnly(True)
        lay.addWidget(self._speed_results, 1)

        start_btn = self._make_button("Start Test", PRIMARY, "#fff", command=self._run_speed_test)
        lay.addWidget(start_btn, 0, Qt.AlignLeft)

        self._tabs.addTab(page, "Speed Test")

    def _speed_load_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Proxy File", "", "Text (*.txt);;All (*)")
        if path:
            lines = [l.strip() for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
            self._speed_text.setPlainText("\n".join(lines))
            self._speed_count.setText(f"{len(lines)} proxies loaded from file")
            self._speed_count.setStyleSheet(f"color: {SUCCESS}; font-size: 12px;")

    def _speed_load_cache(self):
        proxy_file = DATA_DIR / "proxies.txt"
        if proxy_file.exists():
            lines = [l.strip() for l in proxy_file.read_text(encoding="utf-8").splitlines() if l.strip()]
            if lines:
                self._speed_text.setPlainText("\n".join(lines))
                self._speed_count.setText(f"{len(lines)} proxies loaded from cache")
                self._speed_count.setStyleSheet(f"color: {SUCCESS}; font-size: 12px;")
                return
        self._speed_count.setText("No cached proxies found")
        self._speed_count.setStyleSheet(f"color: {WARNING}; font-size: 12px;")

    def _speed_scrape(self):
        def _do():
            from proxy import scrape_proxies_sync
            QTimer.singleShot(0, lambda: self._speed_count.setText("Scraping..."))
            all_proxies = scrape_proxies_sync()
            if all_proxies:
                QTimer.singleShot(0, lambda: (
                    self._speed_text.setPlainText("\n".join(all_proxies)),
                    self._speed_count.setText(f"{len(all_proxies)} proxies scraped"),
                    self._speed_count.setStyleSheet(f"color: {SUCCESS}; font-size: 12px;"),
                ))
            else:
                QTimer.singleShot(0, lambda: (
                    self._speed_count.setText("No proxies found"),
                    self._speed_count.setStyleSheet(f"color: {DANGER}; font-size: 12px;"),
                ))
        threading.Thread(target=_do, daemon=True).start()

    def _speed_clear(self):
        self._speed_text.setPlainText("")
        self._speed_count.setText("0 proxies")
        self._speed_count.setStyleSheet(f"color: {MUTED}; font-size: 12px;")

    def _run_speed_test(self):
        raw = self._speed_text.toPlainText().strip()
        if not raw:
            self._speed_lbl.setText("No proxies to test")
            self._speed_lbl.setStyleSheet(f"color: {DANGER}; font-size: 12px;")
            return
        proxies = [l.strip() for l in raw.splitlines() if l.strip()]
        if not proxies:
            self._speed_lbl.setText("No proxies to test")
            self._speed_lbl.setStyleSheet(f"color: {DANGER}; font-size: 12px;")
            return

        self._speed_lbl.setText(f"Testing {len(proxies)} proxies...")
        self._speed_lbl.setStyleSheet(f"color: {PRIMARY}; font-size: 12px;")

        def _do():
            from proxy import ProxyManager
            pm = ProxyManager(proxies, remove_on_fail=False)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                results = loop.run_until_complete(
                    pm.speed_test(concurrency=100, timeout=5.0)
                )
            finally:
                loop.close()
            results.sort(key=lambda x: (not x[2], x[1]))
            working = sum(1 for _, _, ok in results if ok)
            fast = [p for p, lat, ok in results if ok and lat <= 10000]

            def _show():
                self._speed_bar.setValue(100)
                self._speed_lbl.setText(f"Done: {working} alive, {len(fast)} fast (<=10s)")
                self._speed_lbl.setStyleSheet(
                    f"color: {SUCCESS if working > 0 else DANGER}; font-size: 12px;"
                )
                lines = [f"{'#':<4} {'Proxy':<35} {'Latency':<10} {'Status'}"]
                lines.append("\u2500" * 60)
                for i, (proxy, lat, ok) in enumerate(results[:30], 1):
                    status = f"{lat:.0f}ms" if ok else "FAIL"
                    tag = "OK" if ok and lat <= 10000 else "SLOW" if ok else "FAIL"
                    lines.append(f"{i:<4} {proxy:<35} {status:<10} {tag}")
                if len(results) > 30:
                    lines.append(f"\n...and {len(results) - 30} more")
                self._speed_results.setPlainText("\n".join(lines))

                if fast:
                    fast_file = DATA_DIR / "proxies_fast.txt"
                    fast_file.write_text("\n".join(fast), encoding="utf-8")

            QTimer.singleShot(0, _show)

        threading.Thread(target=_do, daemon=True).start()

    def _show_hits(self):
        self._tabs.clear()
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(30, 20, 30, 20)

        t = QLabel("Available Usernames")
        t.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {TXT};")
        lay.addWidget(t)
        lay.addSpacing(16)

        hits_file = DATA_DIR / "hits.txt"
        if not hits_file.exists():
            lay.addWidget(QLabel("No hits file found."))
            lay.addStretch()
            self._tabs.addTab(page, "Hits")
            return

        hits = [l.strip() for l in hits_file.read_text(encoding="utf-8").splitlines() if l.strip()]
        if not hits:
            lay.addWidget(QLabel("No hits yet."))
            lay.addStretch()
            self._tabs.addTab(page, "Hits")
            return

        lbl = QLabel(f"Found {len(hits)} available usernames:")
        lbl.setStyleSheet(f"color: {SUCCESS}; font-weight: bold;")
        lay.addWidget(lbl)
        lay.addSpacing(8)

        text = QPlainTextEdit()
        text.setReadOnly(True)
        text.setPlainText("\n".join(f"  {i}. {h}" for i, h in enumerate(hits[:100], 1)))
        lay.addWidget(text, 1)

        if len(hits) > 100:
            more = QLabel(f"...and {len(hits) - 100} more")
            more.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
            lay.addWidget(more)

        self._tabs.addTab(page, "Hits")

    def _show_clear_auth(self):
        self._tabs.clear()
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(30, 20, 30, 20)

        t = QLabel("Clear All Auth Data")
        t.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {DANGER};")
        lay.addWidget(t)
        lay.addSpacing(8)
        sub = QLabel("This will delete all tokens, sessions, and auth data.")
        sub.setStyleSheet(f"color: {WARNING}; font-size: 12px;")
        lay.addWidget(sub)
        lay.addSpacing(24)

        lay.addWidget(QLabel("Affected files:"))
        for f in [AUTH_FILE, SESSION_FILE, ACTIVATION_FILE, TOKENS_FILE]:
            status = "Exists" if f.exists() else "Not found"
            color = WARNING if f.exists() else MUTED
            lbl = QLabel(f"  {f.name}: {status}")
            lbl.setStyleSheet(f"color: {color}; font-family: '{_mono}'; font-size: 12px;")
            lay.addWidget(lbl)

        lay.addStretch()

        def _clear():
            reply = QMessageBox.question(
                self, "ew\u00B2", "Are you sure you want to delete ALL auth data?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                for f in [AUTH_FILE, SESSION_FILE, ACTIVATION_FILE]:
                    if f.exists():
                        f.unlink()
                if TOKENS_FILE.exists():
                    TOKENS_FILE.write_text("[]", encoding="utf-8")
                QMessageBox.information(self, "ew\u00B2", "All auth data cleared.")
                self._show_session()

        btn = self._make_button("Clear All Auth", DANGER, "#fff", "#F04040", _clear)
        lay.addWidget(btn, 0, Qt.AlignLeft)

        self._tabs.addTab(page, "Clear Auth")


def main():
    if not HAS_PYSIDE6:
        raise RuntimeError(
            "PySide6 is not installed. Install with:\n"
            "  pip install PySide6\n"
            "Then retry, or use --terminal mode."
        )
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = ModApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
