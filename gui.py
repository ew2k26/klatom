#!/usr/bin/env python3
"""ew² v4.0 - Modern PySide6 GUI."""

from __future__ import annotations

import asyncio
import itertools
import json
import sys
import threading
import time
from pathlib import Path

try:
    from PySide6.QtCore import (
        Qt, QTimer, Signal, QThread, QObject, Slot, QSize,
    )
    from PySide6.QtGui import (
        QFont, QColor, QPalette, QIcon, QPixmap, QPainter,
    )
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QStackedWidget, QLabel, QLineEdit, QPushButton, QRadioButton,
        QButtonGroup, QCheckBox, QSlider, QTextEdit, QProgressBar,
        QFileDialog, QMessageBox, QFrame, QScrollArea, QSizePolicy,
        QSpacerItem, QGridLayout, QTabWidget, QPlainTextEdit,
    )
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

from config import (
    DATA_DIR, LOGS_DIR, RESULTS_DIR, VERSION,
    FONT_FAMILY, FONT_MONO,
    AppSettings, Config, RunConfig, Stats,
    ensure_dir, ensure_file, load_lines, is_valid_username,
    USERNAME_CHARS, MAX_CONCURRENCY,
    C as Colors,
)

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
        selection-background-color: {PRIMARY_L};
    }}
    QLineEdit:focus {{ border: 1px solid {PRIMARY_L}; }}
    QLineEdit[echoMode="2"] {{ font-family: "{_mono}"; }}
    QPushButton {{
        background-color: {PRIMARY}; color: #fff; border: none;
        border-radius: 6px; padding: 10px 24px; font-weight: bold;
        font-size: 13px; min-height: 20px;
    }}
    QPushButton:hover {{ background-color: {PRIMARY_L}; }}
    QPushButton:pressed {{ background-color: {PRIMARY_D}; }}
    QPushButton:disabled {{ background-color: {BG3}; color: {MUTED}; }}
    QPushButton#accent {{
        background-color: {SUCCESS}; color: #fff;
    }}
    QPushButton#accent:hover {{ background-color: #30D848; }}
    QPushButton#danger {{
        background-color: {DANGER}; color: #fff;
    }}
    QPushButton#danger:hover {{ background-color: #F04040; }}
    QPushButton#ghost {{
        background-color: transparent; color: {TXT2};
        border: 1px solid {BORDER};
    }}
    QPushButton#ghost:hover {{ background-color: {BG3}; color: {TXT}; border-color: {PRIMARY_L}; }}
    QRadioButton {{
        spacing: 8px; color: {TXT}; font-size: 13px;
    }}
    QRadioButton::indicator {{
        width: 18px; height: 18px; border: 2px solid {BORDER2};
        border-radius: 10px; background: {BG3};
    }}
    QRadioButton::indicator:checked {{
        background: {PRIMARY_L}; border: 2px solid {PRIMARY_L};
    }}
    QRadioButton::indicator:hover {{ border-color: {PRIMARY_L}; }}
    QCheckBox {{
        spacing: 8px; color: {TXT2}; font-size: 12px;
    }}
    QCheckBox::indicator {{
        width: 18px; height: 18px; border: 2px solid {BORDER2};
        border-radius: 4px; background: {BG3};
    }}
    QCheckBox::indicator:checked {{
        background: {PRIMARY_L}; border: 2px solid {PRIMARY_L};
    }}
    QSlider::groove:horizontal {{
        height: 6px; background: {BG3}; border-radius: 3px;
    }}
    QSlider::handle:horizontal {{
        background: {PRIMARY_L}; width: 18px; height: 18px;
        margin: -6px 0; border-radius: 9px;
    }}
    QSlider::handle:horizontal:hover {{ background: {TXT2}; }}
    QProgressBar {{
        background-color: {BG3}; border: none; border-radius: 4px;
        height: 8px; text-align: center; color: transparent;
    }}
    QProgressBar::chunk {{ background-color: {PRIMARY_L}; border-radius: 4px; }}
    QProgressBar[accentColor="green"]::chunk {{ background-color: {SUCCESS}; }}
    QScrollBar:vertical {{
        background: {BG}; width: 8px; margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {BORDER2}; min-height: 30px; border-radius: 4px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {PRIMARY_L}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
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
    QPlainTextEdit, QTextEdit {{
        background-color: {BG3}; color: {TXT2}; border: 1px solid {BORDER};
        border-radius: 6px; padding: 8px; font-family: "{_mono}"; font-size: 12px;
    }}
    QPlainTextEdit:focus, QTextEdit:focus {{ border: 1px solid {PRIMARY_L}; }}
    QToolTip {{
        background: {BG3}; color: {TXT}; border: 1px solid {BORDER2};
        padding: 6px; border-radius: 4px; font-size: 12px;
    }}
    """


class AsyncWorker(QObject):
    result = Signal(object)
    error = Signal(str)
    progress = Signal(float)
    status = Signal(str)

    def __init__(self):
        super().__init__()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

    def start(self):
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def submit(self, coro):
        if self._loop is None:
            self.error.emit("Worker not started")
            return
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        def _done(f):
            try:
                self.result.emit(f.result())
            except Exception as e:
                self.error.emit(str(e))
        future.add_done_callback(_done)

    @property
    def is_ready(self):
        return self._loop is not None and self._loop.is_running()

    def stop(self):
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=2)


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"ew\u00B2 v{VERSION}")
        self.setMinimumSize(760, 600)
        self.resize(820, 640)
        self.setStyleSheet(STYLESHEET)
        self._set_icon()
        self.config = Config()
        self._wizard_data = {}
        self._async = AsyncWorker()
        self._async.result.connect(self._on_async_result)
        self._async.error.connect(self._on_async_error)
        self._async.status.connect(self._on_async_status)
        self._async.start()
        self._stop_event = threading.Event()
        self._build_ui()
        self._wait_timer = QTimer(self)
        self._wait_timer.timeout.connect(self._check_ready)
        self._wait_timer.start(100)

    def _check_ready(self):
        if self._async.is_ready:
            self._wait_timer.stop()
            self._show_auth()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._header = self._make_header()
        layout.addWidget(self._header)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        self._stack = QStackedWidget()
        body_layout.addWidget(self._stack)
        layout.addWidget(body, 1)

    def _make_header(self):
        h = QFrame()
        h.setFixedHeight(56)
        h.setStyleSheet(f"background: {BG2}; border-bottom: 1px solid {BORDER};")
        lay = QHBoxLayout(h)
        lay.setContentsMargins(24, 0, 24, 0)
        t = QLabel()
        t.setText(f'<span style="color:{PRIMARY};font-size:22px;font-weight:bold">ew</span>'
                  f'<span style="color:{TXT};font-size:22px;font-weight:bold">\u00B2</span>'
                  f'<span style="color:{MUTED};font-size:13px;margin-left:12px">v{VERSION}</span>')
        lay.addWidget(t)
        lay.addStretch()
        self._status_lbl = QLabel("  Ready  ")
        self._status_lbl.setStyleSheet(
            f"color: {SUCCESS}; background: {BG3}; padding: 4px 12px; border-radius: 4px; font-size: 11px;"
        )
        lay.addWidget(self._status_lbl)
        return h

    def _set_status(self, text, color=None):
        c = color or PRIMARY
        self._status_lbl.setText(f"  {text}  ")
        self._status_lbl.setStyleSheet(
            f"color: {c}; background: {BG3}; padding: 4px 12px; border-radius: 4px; font-size: 11px;"
        )

    def _clear_stack(self):
        while self._stack.count():
            w = self._stack.widget(0)
            self._stack.removeWidget(w)
            w.deleteLater()

    # ── Async helpers ──
    def _on_async_error(self, msg):
        self._set_status("Error", DANGER)

    def _on_async_status(self, msg):
        self._set_status(msg, WARNING)

    # ── AUTH SCREEN ──
    def _show_auth(self):
        self._clear_stack()
        self._set_status("Auth", WARNING)
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(0)

        inner = QWidget()
        inner.setMaximumWidth(440)
        il = QVBoxLayout(inner)
        il.setContentsMargins(0, 0, 0, 0)
        il.setSpacing(0)

        il.addSpacing(60)
        t = QLabel()
        t.setText(f'<span style="color:{PRIMARY};font-size:28px;font-weight:bold">Welcome to ew\u00B2</span>')
        t.setAlignment(Qt.AlignCenter)
        il.addWidget(t)
        il.addSpacing(8)
        sub = QLabel("License authentication required")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(f"color: {MUTED}; font-size: 13px;")
        il.addWidget(sub)
        il.addSpacing(36)

        lbl = QLabel("License Token")
        lbl.setStyleSheet(f"color: {TXT2}; font-weight: bold; font-size: 12px;")
        il.addWidget(lbl)
        il.addSpacing(6)
        self._token_input = QLineEdit()
        self._token_input.setPlaceholderText("EW2-XXXX-XXXX-XXXX")
        self._token_input.setEchoMode(QLineEdit.Password)
        self._token_input.returnPressed.connect(self._submit_token)
        il.addWidget(self._token_input)
        il.addSpacing(20)

        bl = QHBoxLayout()
        bl.setSpacing(10)
        btn_activate = QPushButton("Activate License")
        btn_activate.clicked.connect(self._submit_token)
        bl.addWidget(btn_activate)
        btn_trial = QPushButton("Free Trial (24h)")
        btn_trial.setObjectName("ghost")
        btn_trial.clicked.connect(self._start_trial)
        bl.addWidget(btn_trial)
        il.addLayout(bl)

        il.addSpacing(16)
        self._auth_msg = QLabel()
        self._auth_msg.setAlignment(Qt.AlignCenter)
        self._auth_msg.setStyleSheet(f"color: {DANGER}; font-size: 12px;")
        self._auth_msg.setWordWrap(True)
        il.addWidget(self._auth_msg)

        lay.addWidget(inner)
        self._stack.addWidget(page)
        self._stack.setCurrentWidget(page)
        self._check_existing_auth()

    def _check_existing_auth(self):
        from crypto import load_auth, hash_token, is_machine_activated, load_activation
        activation_file = DATA_DIR / ".activation"
        session_file = DATA_DIR / ".session"

        # 1. Check activation (one-time token activation)
        if is_machine_activated(activation_file):
            try:
                data = load_activation(activation_file)
                if data:
                    self._auth_msg.setText("License active")
                    self._auth_msg.setStyleSheet(f"color: {SUCCESS}; font-size: 12px;")
                    QTimer.singleShot(300, lambda: self._async.result.emit("auth_ok"))
                    return
            except Exception:
                pass

        # 2. Check trial session
        if session_file.exists():
            try:
                from crypto import load_session
                data = load_session(session_file)
                if data:
                    start = data.get("ts", 0)
                    hwid = data.get("th", "")
                    from crypto import get_hwid
                    if start and (not hwid or hwid == get_hwid()):
                        if (time.time() - start) < 86400:
                            self._auth_msg.setText("Trial session active")
                            self._auth_msg.setStyleSheet(f"color: {SUCCESS}; font-size: 12px;")
                            QTimer.singleShot(500, lambda: self._async.result.emit("auth_ok"))
                            return
            except Exception:
                pass

        # 3. Check legacy CREATOR auth
        auth_file = DATA_DIR / ".auth"
        if auth_file.exists():
            try:
                data = load_auth(auth_file)
                if data and hash_token("CREATOR") in data.get("t", []):
                    self._auth_msg.setText("Creator access")
                    self._auth_msg.setStyleSheet(f"color: {SUCCESS}; font-size: 12px;")
                    QTimer.singleShot(500, lambda: self._async.result.emit("auth_ok"))
                    return
            except Exception:
                pass

    def _submit_token(self):
        token = self._token_input.text().strip()
        if not token:
            self._auth_msg.setText("Enter a license token")
            self._auth_msg.setStyleSheet(f"color: {DANGER}; font-size: 12px;")
            return

        # Try one-time activation
        from auth import activate_token, is_token_approved, add_approved_token
        if activate_token(token):
            self._auth_msg.setText("Token activated")
            self._auth_msg.setStyleSheet(f"color: {SUCCESS}; font-size: 12px;")
            QTimer.singleShot(400, lambda: self._async.result.emit("auth_ok"))
            return

        # Legacy: check if already approved
        if is_token_approved(token):
            self._auth_msg.setText("Token approved")
            self._auth_msg.setStyleSheet(f"color: {SUCCESS}; font-size: 12px;")
            QTimer.singleShot(400, lambda: self._async.result.emit("auth_ok"))
            return

        auth_file = DATA_DIR / ".auth"
        from crypto import load_auth
        data = load_auth(auth_file)
        if data is None or not data.get("t"):
            add_approved_token("CREATOR")
            add_approved_token(token)
            self._auth_msg.setText("Creator token registered")
            self._auth_msg.setStyleSheet(f"color: {SUCCESS}; font-size: 12px;")
            QTimer.singleShot(400, lambda: self._async.result.emit("auth_ok"))
            return
        self._auth_msg.setText("Invalid, expired, or revoked token")
        self._auth_msg.setStyleSheet(f"color: {DANGER}; font-size: 12px;")

    def _start_trial(self):
        from auth import _activate_trial
        _activate_trial()
        self._auth_msg.setText("Free trial activated (24h)")
        self._auth_msg.setStyleSheet(f"color: {SUCCESS}; font-size: 12px;")
        QTimer.singleShot(400, lambda: self._async.result.emit("auth_ok"))

    # ── WIZARD ──
    def _show_wizard(self):
        self._clear_stack()
        self._set_status("Setup", PRIMARY)
        self._wizard_data = {
            "proxies": [], "scraped": False, "remove_bad": True,
            "usernames": [], "concurrency": 50, "timeout": 10,
            "webhook_url": None, "webhook_msg": None,
        }
        self._build_wizard(0)

    def _build_wizard(self, step):
        self._clear_stack()
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._make_step_bar(step))
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        lay.addWidget(sep)
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(40, 20, 40, 20)
        steps = [self._step_proxy, self._step_speed, self._step_names,
                 self._step_perf, self._step_webhook, self._step_summary]
        steps[step](cl)
        lay.addWidget(content, 1)
        self._stack.addWidget(page)
        self._stack.setCurrentWidget(page)

    def _make_step_bar(self, current):
        w = QWidget()
        w.setFixedHeight(48)
        l = QHBoxLayout(w)
        l.setContentsMargins(40, 0, 40, 0)
        for i, name in enumerate(["Proxies", "Speed", "Usernames", "Performance", "Webhook"]):
            if i > 0:
                sep = QLabel("\u2022")
                sep.setStyleSheet(f"color: {BORDER}; font-size: 10px;")
                l.addWidget(sep)
            c = SUCCESS if i < current else PRIMARY if i == current else MUTED
            b = "bold" if i == current else "normal"
            lbl = QLabel(name)
            lbl.setStyleSheet(f"color: {c}; font-size: 12px; font-weight: {b};")
            l.addWidget(lbl)
        l.addStretch()

    def _step_proxy(self, lay):
        t = QLabel("Proxy Source")
        t.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {TXT};")
        lay.addWidget(t)
        lay.addSpacing(4)
        sub = QLabel("Proxies strongly recommended to avoid rate-limiting")
        sub.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        lay.addWidget(sub)
        lay.addSpacing(20)

        self._proxy_grp = QButtonGroup(self)

        for val, label, desc in [
            ("file", "From File", "Load proxies from a text file"),
            ("paste", "Paste", "Paste proxies directly"),
            ("scrape", "Scrape Free", "Auto-fetch from 17 public sources"),
            ("none", "None", "Run without proxies (rate-limited)"),
        ]:
            rf = QWidget()
            rl = QHBoxLayout(rf)
            rl.setContentsMargins(0, 4, 0, 4)
            rb = QRadioButton(label)
            rb.setStyleSheet("font-weight: bold; font-size: 13px;")
            rl.addWidget(rb)
            self._proxy_grp.addButton(rb)
            self._proxy_grp.setId(rb, ["file", "paste", "scrape", "none"].index(val))
            if val == "file":
                rb.setChecked(True)
            dl = QLabel(desc)
            dl.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
            rl.addWidget(dl)
            rl.addStretch()
            lay.addWidget(rf)

        self._proxy_file_w = QWidget()
        fl = QVBoxLayout(self._proxy_file_w)
        fl.setContentsMargins(26, 8, 0, 0)
        fl.setSpacing(6)
        fl.addWidget(QLabel("Proxy File"))
        fr = QHBoxLayout()
        default_path = str(DATA_DIR / "proxies.txt")
        self._proxy_path = QLineEdit(default_path)
        fr.addWidget(self._proxy_path, 1)
        browse = QPushButton("Browse")
        browse.setFixedWidth(80)
        browse.setObjectName("ghost")
        browse.clicked.connect(self._browse_proxy)
        fr.addWidget(browse)
        fl.addLayout(fr)
        lay.addWidget(self._proxy_file_w)

        self._proxy_paste_w = QWidget()
        pl = QVBoxLayout(self._proxy_paste_w)
        pl.setContentsMargins(26, 8, 0, 0)
        pl.addWidget(QLabel("Paste proxies (one per line):"))
        self._proxy_paste = QPlainTextEdit()
        self._proxy_paste.setPlaceholderText("login:pass@host:port")
        self._proxy_paste.setMaximumHeight(120)
        pl.addWidget(self._proxy_paste)
        lay.addWidget(self._proxy_paste_w)
        self._proxy_paste_w.hide()

        self._proxy_grp.buttonClicked.connect(self._on_proxy_radio)

        cb = QCheckBox("Auto-remove dead proxies")
        cb.setChecked(True)
        cb.toggled.connect(lambda v: self._wizard_data.__setitem__("remove_bad", v))
        lay.addWidget(cb)

        lay.addStretch()
        btn = QPushButton("Next  \u2192")
        btn.clicked.connect(self._finish_proxy)
        lay.addWidget(btn, 0, Qt.AlignRight)

    def _on_proxy_radio(self):
        checked = self._proxy_grp.checkedId()
        self._proxy_file_w.setVisible(checked == 0)
        self._proxy_paste_w.setVisible(checked == 1)

    def _browse_proxy(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Proxy File", "", "Text files (*.txt);;All files (*)"
        )
        if path:
            self._proxy_path.setText(path)

    def _finish_proxy(self):
        src = ["file", "paste", "scrape", "none"][self._proxy_grp.checkedId()]
        if src == "file":
            self._wizard_data["proxies"] = load_lines(self._proxy_path.text())
        elif src == "paste":
            raw = self._proxy_paste.toPlainText()
            self._wizard_data["proxies"] = [l.strip() for l in raw.splitlines() if l.strip()]
        elif src == "scrape":
            self._set_status("Scraping", WARNING)
            self._async.submit(self._do_scrape())
            return
        self._wizard_data["scraped"] = False
        n = len(self._wizard_data["proxies"])
        step = 1 if n > 10 and src == "scrape" else 2
        self._build_wizard(step)

    async def _do_scrape(self):
        from proxy import scrape_proxies
        self._async.status.emit("Scraping proxies...")
        all_proxies = await scrape_proxies()
        return ("scrape_done", all_proxies)

    def _step_speed(self, lay):
        n = len(self._wizard_data["proxies"])
        t = QLabel("Speed Test")
        t.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {TXT};")
        lay.addWidget(t)
        lay.addSpacing(4)
        sub = QLabel(f"Test {n} scraped proxies for latency and availability")
        sub.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        lay.addWidget(sub)
        lay.addSpacing(20)
        self._speed_bar = QProgressBar()
        lay.addWidget(self._speed_bar)
        lay.addSpacing(8)
        self._speed_lbl = QLabel("Ready to test")
        self._speed_lbl.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        lay.addWidget(self._speed_lbl)
        lay.addSpacing(16)
        bl = QHBoxLayout()
        btn = QPushButton("Start Speed Test")
        btn.clicked.connect(self._run_speed_test)
        bl.addWidget(btn)
        skip = QPushButton("Skip")
        skip.setObjectName("ghost")
        skip.clicked.connect(lambda: self._build_wizard(2))
        bl.addWidget(skip)
        bl.addStretch()
        lay.addLayout(bl)
        lay.addStretch()

    def _run_speed_test(self):
        self._speed_lbl.setText("Testing...")
        self._speed_lbl.setStyleSheet(f"color: {PRIMARY}; font-size: 12px;")
        self._async.submit(self._do_speed_test())

    async def _do_speed_test(self):
        from proxy import ProxyManager
        proxies = list(self._wizard_data["proxies"])
        pm = ProxyManager(proxies, remove_on_fail=True, scored=True)
        results = await pm.speed_test(concurrency=100, timeout=5.0)
        working = await pm.apply_speed_results(results, remove_slow=True, max_latency_ms=10000)
        working_proxies = [r[0] for r in results if r[2] and r[1] <= 10000]
        if not working_proxies:
            working_proxies = [r[0] for r in results if r[2]]
        return ("speed_done", (working, working_proxies, len(proxies)))

    def _handle_speed_done(self, data):
        working, working_proxies, total = data
        self._wizard_data["proxies"] = working_proxies
        self._speed_bar.setValue(100)
        self._speed_lbl.setText(f"Done: {working} working proxies (of {total})")
        self._speed_lbl.setStyleSheet(f"color: {SUCCESS if working > 0 else DANGER}; font-size: 12px;")
        QTimer.singleShot(1000, lambda: self._build_wizard(2))

    def _step_names(self, lay):
        t = QLabel("Usernames")
        t.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {TXT};")
        lay.addWidget(t)
        lay.addSpacing(20)

        self._names_grp = QButtonGroup(self)
        for val, label in [("file", "Load from File"), ("generate", "Generate Random")]:
            rf = QWidget()
            rl = QHBoxLayout(rf)
            rl.setContentsMargins(0, 4, 0, 4)
            rb = QRadioButton(label)
            rb.setStyleSheet("font-size: 13px;")
            rl.addWidget(rb)
            self._names_grp.addButton(rb)
            self._names_grp.setId(rb, 0 if val == "file" else 1)
            if val == "file":
                rb.setChecked(True)
            rl.addStretch()
            lay.addWidget(rf)

        self._names_file_w = QWidget()
        nfl = QHBoxLayout(self._names_file_w)
        nfl.setContentsMargins(26, 8, 0, 0)
        self._names_path = QLineEdit(str(DATA_DIR / "names_to_check.txt"))
        nfl.addWidget(self._names_path, 1)
        browse = QPushButton("Browse")
        browse.setFixedWidth(80)
        browse.setObjectName("ghost")
        browse.clicked.connect(self._browse_names)
        nfl.addWidget(browse)
        lay.addWidget(self._names_file_w)

        self._names_gen_w = QWidget()
        ngl = QHBoxLayout(self._names_gen_w)
        ngl.setContentsMargins(26, 8, 0, 0)
        ngl.addWidget(QLabel("Length:"))
        self._names_len = QButtonGroup(self)
        for i, length in enumerate(["3", "4", "5"]):
            rb = QRadioButton(f"{length} chars")
            rb.setStyleSheet("font-size: 12px;")
            self._names_len.addButton(rb)
            self._names_len.setId(rb, int(length))
            ngl.addWidget(rb)
            if length == "4":
                rb.setChecked(True)
        ngl.addStretch()
        lay.addWidget(self._names_gen_w)
        self._names_gen_w.hide()

        self._names_grp.buttonClicked.connect(self._on_names_radio)
        lay.addStretch()
        btn = QPushButton("Next  \u2192")
        btn.clicked.connect(self._finish_names)
        lay.addWidget(btn, 0, Qt.AlignRight)

    def _on_names_radio(self):
        is_gen = self._names_grp.checkedId() == 1
        self._names_file_w.setVisible(not is_gen)
        self._names_gen_w.setVisible(is_gen)

    def _browse_names(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Username File", "", "Text files (*.txt);;All files (*)"
        )
        if path:
            self._names_path.setText(path)

    def _finish_names(self):
        if self._names_grp.checkedId() == 0:
            usernames = load_lines(self._names_path.text())
        else:
            length = self._names_len.checkedId()
            chars = USERNAME_CHARS
            if length >= 5:
                seen = set()
                usernames = []
                import random as _rand
                while len(usernames) < 50000:
                    cand = "".join(_rand.choices(chars, k=length))
                    if cand not in seen and is_valid_username(cand):
                        seen.add(cand)
                        usernames.append(cand)
            else:
                combos = ["".join(c) for c in itertools.product(chars, repeat=length)]
                usernames = [c for c in combos if is_valid_username(c)]
                import random as _rand
                usernames = _rand.sample(usernames, min(50000, len(usernames)))
        if not usernames:
            QMessageBox.warning(self, "ew\u00B2", "No usernames found or generated.")
            return
        self._wizard_data["usernames"] = usernames
        self._build_wizard(3)

    def _step_perf(self, lay):
        t = QLabel("Performance")
        t.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {TXT};")
        lay.addWidget(t)
        lay.addSpacing(20)

        scraped = self._wizard_data["scraped"]
        proxies = self._wizard_data["proxies"]

        lay.addWidget(QLabel("Concurrent Workers"))
        if scraped:
            default_conc = 100
        elif proxies:
            default_conc = min(MAX_CONCURRENCY, max(10, len(proxies) * 5))
        else:
            default_conc = 1
        self._conc_slider = QSlider(Qt.Horizontal)
        self._conc_slider.setRange(1, min(2000, MAX_CONCURRENCY))
        self._conc_slider.setValue(default_conc)
        self._conc_lbl = QLabel(str(default_conc))
        self._conc_lbl.setStyleSheet(f"color: {PRIMARY}; font-weight: bold;")
        self._conc_slider.valueChanged.connect(lambda v: self._conc_lbl.setText(str(v)))
        sl = QHBoxLayout()
        sl.addWidget(self._conc_slider, 1)
        sl.addWidget(self._conc_lbl)
        lay.addLayout(sl)
        lay.addSpacing(16)

        lay.addWidget(QLabel("Request Timeout (seconds)"))
        default_timeout = 5 if scraped else 10
        self._timeout_slider = QSlider(Qt.Horizontal)
        self._timeout_slider.setRange(1, 30)
        self._timeout_slider.setValue(default_timeout)
        self._timeout_lbl = QLabel(str(default_timeout))
        self._timeout_lbl.setStyleSheet(f"color: {PRIMARY}; font-weight: bold;")
        self._timeout_slider.valueChanged.connect(lambda v: self._timeout_lbl.setText(str(v)))
        sl2 = QHBoxLayout()
        sl2.addWidget(self._timeout_slider, 1)
        sl2.addWidget(self._timeout_lbl)
        lay.addLayout(sl2)

        if not proxies:
            lay.addSpacing(12)
            lbl = QLabel("Proxyless mode: 1 worker with delay")
            lbl.setStyleSheet(f"color: {WARNING}; font-size: 12px;")
            lay.addWidget(lbl)

        lay.addStretch()
        btn = QPushButton("Next  \u2192")
        btn.clicked.connect(self._finish_perf)
        lay.addWidget(btn, 0, Qt.AlignRight)

    def _finish_perf(self):
        self._wizard_data["concurrency"] = self._conc_slider.value()
        self._wizard_data["timeout"] = self._timeout_slider.value()
        self._build_wizard(4)

    def _step_webhook(self, lay):
        t = QLabel("Discord Webhook")
        t.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {TXT};")
        lay.addWidget(t)
        lay.addSpacing(4)
        sub = QLabel("Optional: get notified when usernames are found")
        sub.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        lay.addWidget(sub)
        lay.addSpacing(16)

        self._webhook_cb = QCheckBox("Send hits to Discord webhook")
        lay.addWidget(self._webhook_cb)

        self._webhook_fields = QWidget()
        wfl = QVBoxLayout(self._webhook_fields)
        wfl.setContentsMargins(0, 12, 0, 0)
        wfl.setSpacing(6)
        wfl.addWidget(QLabel("Webhook URL"))
        self._webhook_url = QLineEdit()
        self._webhook_url.setPlaceholderText("https://discord.com/api/webhooks/...")
        wfl.addWidget(self._webhook_url)
        wfl.addSpacing(8)
        wfl.addWidget(QLabel("Message Template"))
        lbl = QLabel("Placeholders: <name>, <time>, <elapsed>")
        lbl.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        wfl.addWidget(lbl)
        self._webhook_msg = QLineEdit("**<name>** available | <t:time:R>")
        wfl.addWidget(self._webhook_msg)
        lay.addWidget(self._webhook_fields)

        saved_url = self.config.get("webhook", "")
        if saved_url:
            self._webhook_cb.setChecked(True)
            self._webhook_url.setText(saved_url)
            self._webhook_msg.setText(
                self.config.get("webhook_message", "**<name>** available | <t:time:R>")
            )
        else:
            self._webhook_fields.hide()

        self._webhook_cb.toggled.connect(
            lambda v: self._webhook_fields.setVisible(v)
        )
        lay.addStretch()
        btn = QPushButton("Next  \u2192")
        btn.clicked.connect(self._finish_webhook)
        lay.addWidget(btn, 0, Qt.AlignRight)

    def _finish_webhook(self):
        if self._webhook_cb.isChecked():
            url = self._webhook_url.text().strip()
            msg = self._webhook_msg.text().strip()
            self._wizard_data["webhook_url"] = url or None
            self._wizard_data["webhook_msg"] = msg or None
            if url:
                self.config.set("webhook", url)
                self.config.set("webhook_message", msg)
        self._build_wizard(5)

    def _step_summary(self, lay):
        t = QLabel("Ready to Start")
        t.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {TXT};")
        lay.addWidget(t)
        lay.addSpacing(16)

        d = self._wizard_data
        card = QFrame()
        card.setStyleSheet(f"background: {BG2}; border: 1px solid {BORDER}; border-radius: 8px;")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.setSpacing(10)
        items = [
            ("Proxies", f"{len(d['proxies'])} {'(free/scraped)' if d['scraped'] else ''}"),
            ("Usernames", str(len(d["usernames"]))),
            ("Workers", str(d["concurrency"])),
            ("Timeout", f"{d['timeout']}s"),
            ("Webhook", "On" if d["webhook_url"] else "Off"),
        ]
        for label, value in items:
            row = QHBoxLayout()
            row.addWidget(self._summary_label(label))
            row.addWidget(self._summary_value(value))
            row.addStretch()
            cl.addLayout(row)
        lay.addWidget(card)
        lay.addStretch()

        bl = QHBoxLayout()
        back = QPushButton("\u2190 Back")
        back.setObjectName("ghost")
        back.clicked.connect(lambda: self._build_wizard(4))
        bl.addWidget(back)
        bl.addStretch()
        start = QPushButton("Start Checking")
        start.setObjectName("accent")
        start.clicked.connect(self._start_checking)
        bl.addWidget(start)
        lay.addLayout(bl)

    def _summary_label(self, text):
        lbl = QLabel(text)
        lbl.setFixedWidth(120)
        lbl.setStyleSheet(f"color: {MUTED}; font-size: 13px;")
        return lbl

    def _summary_value(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {TXT}; font-weight: bold; font-size: 13px;")
        return lbl

    # ── CHECKING ──
    def _start_checking(self):
        d = self._wizard_data
        if not d["usernames"]:
            QMessageBox.warning(self, "ew\u00B2", "No usernames to check.")
            return
        self._stop_event.clear()
        self._show_checking_screen()

    def _show_checking_screen(self):
        self._clear_stack()
        self._set_status("Running", SUCCESS)
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(20, 16, 20, 16)

        self._check_bar = QProgressBar()
        self._check_bar.setObjectName("green")
        self._check_bar.setStyleSheet(
            f"QProgressBar {{ background-color: {BG3}; border: none; border-radius: 4px; height: 8px; }}"
            f" QProgressBar::chunk {{ background-color: {SUCCESS}; border-radius: 4px; }}"
        )
        lay.addWidget(self._check_bar)
        lay.addSpacing(8)

        grid = QGridLayout()
        grid.setSpacing(8)
        self._stat_lbls = {}
        self._last_feed_counts = {"works": 0, "taken": 0, "errors": 0}
        for i, (key, label, color) in enumerate([
            ("available", "Available", SUCCESS),
            ("taken", "Taken", DANGER),
            ("reqs", "Requests", PRIMARY),
            ("rps", "Req/s", PRIMARY),
            ("errors", "Errors", DANGER),
            ("elapsed", "Elapsed", MUTED),
        ]):
            card = QFrame()
            card.setStyleSheet(
                f"background: {BG2}; border: 1px solid {BORDER}; border-radius: 6px; padding: 8px;"
            )
            cl = QVBoxLayout(card)
            cl.setContentsMargins(12, 8, 12, 8)
            cl.setSpacing(2)
            ll = QLabel(label)
            ll.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
            cl.addWidget(ll)
            vl = QLabel("0")
            vl.setStyleSheet(f"color: {color}; font-size: 20px; font-weight: bold;")
            cl.addWidget(vl)
            self._stat_lbls[key] = vl
            grid.addWidget(card, i // 3, i % 3)
        lay.addLayout(grid)
        lay.addSpacing(8)

        al = QLabel("Activity")
        al.setStyleSheet(f"color: {TXT2}; font-weight: bold; font-size: 12px;")
        lay.addWidget(al)
        self._feed = QPlainTextEdit()
        self._feed.setReadOnly(True)
        self._feed.setMaximumHeight(160)
        lay.addWidget(self._feed)

        bl = QHBoxLayout()
        bl.addStretch()
        stop = QPushButton("Stop")
        stop.setObjectName("danger")
        stop.clicked.connect(self._stop_checking)
        bl.addWidget(stop)
        lay.addLayout(bl)

        self._stack.addWidget(page)
        self._stack.setCurrentWidget(page)
        self._run_checking_async()

    def _run_checking_async(self):
        d = self._wizard_data
        proxies = list(d["proxies"])
        usernames = list(d["usernames"])
        concurrency = d["concurrency"]
        timeout = d["timeout"]
        scraped = d["scraped"]
        webhook_url = d.get("webhook_url")
        webhook_msg = d.get("webhook_msg")

        if proxies and concurrency > len(proxies):
            concurrency = max(1, len(proxies))
        concurrency = min(concurrency, 100)

        self._async.submit(self._do_check(
            proxies, usernames, concurrency, timeout, scraped, webhook_url, webhook_msg,
        ))

    async def _do_check(self, proxies, usernames, concurrency, timeout, scraped, webhook_url, webhook_msg):
        from proxy import ProxyManager
        from engine import Checker, WebhookSender
        from config import ENDPOINT
        import aiohttp

        pm = ProxyManager(proxies, remove_on_fail=True, scored=scraped)
        stats = Stats()
        start_time = time.time()
        total = len(usernames)
        _idx = [0]
        _lock = asyncio.Lock()
        stop = self._stop_event

        async def _next():
            async with _lock:
                if _idx[0] >= total:
                    return None
                i = _idx[0]
                _idx[0] += 1
                return i, usernames[i]

        connector = aiohttp.TCPConnector(limit=MAX_CONCURRENCY * 2, limit_per_host=0, ttl_dns_cache=300)
        session_timeout = aiohttp.ClientTimeout(total=None, sock_connect=5, sock_read=30)
        session = aiohttp.ClientSession(connector=connector, trust_env=False, timeout=session_timeout)
        checker = Checker(pm, timeout=timeout, scraped=scraped, stats=stats)

        webhook = None
        webhook_task = None
        if webhook_url and webhook_msg:
            webhook = WebhookSender(webhook_url, webhook_msg, session, start_time)
            webhook_task = asyncio.create_task(webhook.run())

        async def _worker():
            while True:
                t = await _next()
                if t is None:
                    return
                _, name = t
                try:
                    result, data, code = await checker.check(session, name)
                    if result is True:
                        await stats.inc_works()
                    elif result is False:
                        await stats.inc_taken()
                    else:
                        await stats.inc_errors()
                        if result in ("EXHAUSTED", "ERROR"):
                            await asyncio.sleep(0.5)
                    if webhook and result is True:
                        webhook.enqueue(name)
                except Exception:
                    await stats.inc_errors()

        tasks = [asyncio.create_task(_worker()) for _ in range(concurrency)]
        last_update = 0

        while not stop.is_set():
            await asyncio.sleep(0.3)
            now = time.time()
            if now - last_update >= 0.5:
                snap = await stats.snapshot()
                elapsed = now - start_time
                pct = (snap["works"] + snap["taken"]) / max(total, 1) * 100
                self._async.result.emit(("check_progress", snap, elapsed, pct))
                last_update = now
            if all(t.done() for t in tasks) and _idx[0] >= total:
                break

        for t in tasks:
            t.cancel()
        if webhook_task:
            webhook_task.cancel()
            try:
                await webhook_task
            except asyncio.CancelledError:
                pass
        await session.close()

        elapsed = time.time() - start_time
        snap = await stats.snapshot()
        return ("check_done", (snap, elapsed))

    def _on_async_result(self, val):
        if val == "auth_ok":
            self._set_status("Setup", SUCCESS)
            QTimer.singleShot(200, self._show_wizard)
        elif isinstance(val, tuple) and len(val) == 2:
            cmd = val[0]
            data = val[1]
            if cmd == "scrape_done":
                self._wizard_data["proxies"] = data
                self._wizard_data["scraped"] = True
                self._build_wizard(1 if len(data) > 10 else 2)
            elif cmd == "speed_done":
                self._handle_speed_done(data)
            elif cmd == "check_done":
                self._show_results(data[0], data[1])
            elif cmd == "check_progress":
                snap, elapsed, pct = data
                self._update_check_ui(snap, elapsed, pct)

    def _update_check_ui(self, snap, elapsed, pct):
        self._check_bar.setValue(min(int(pct), 100))
        self._stat_lbls["available"].setText(str(snap["works"]))
        self._stat_lbls["taken"].setText(str(snap["taken"]))
        self._stat_lbls["reqs"].setText(str(snap["requests"]))
        self._stat_lbls["rps"].setText(f"{snap['requests'] / max(elapsed, 0.1):.0f}")
        self._stat_lbls["errors"].setText(str(snap["errors"]))
        self._stat_lbls["elapsed"].setText(f"{elapsed:.0f}s")

        prev = self._last_feed_counts
        if snap["works"] > prev["works"]:
            diff = snap["works"] - prev["works"]
            self._feed.appendPlainText(f"[{elapsed:.0f}s] +{diff} available found")
        if snap["taken"] > prev["taken"]:
            diff = snap["taken"] - prev["taken"]
            self._feed.appendPlainText(f"[{elapsed:.0f}s] +{diff} taken")
        if snap["errors"] > prev["errors"]:
            diff = snap["errors"] - prev["errors"]
            self._feed.appendPlainText(f"[{elapsed:.0f}s] +{diff} errors")
        prev["works"] = snap["works"]
        prev["taken"] = snap["taken"]
        prev["errors"] = snap["errors"]

    def _stop_checking(self):
        self._stop_event.set()

    def _show_results(self, snap, elapsed):
        self._clear_stack()
        self._set_status("Done", SUCCESS)
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(40, 30, 40, 30)

        t = QLabel("Checking Complete")
        t.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {SUCCESS};")
        lay.addWidget(t)
        lay.addSpacing(20)

        card = QFrame()
        card.setStyleSheet(f"background: {BG2}; border: 1px solid {BORDER}; border-radius: 8px;")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.setSpacing(10)
        for label, value, color in [
            ("Available", str(snap.get("works", 0)), SUCCESS),
            ("Taken", str(snap.get("taken", 0)), DANGER),
            ("Requests", str(snap.get("requests", 0)), TXT),
            ("Rate Limited", str(snap.get("ratelimited", 0)), WARNING),
            ("Errors", str(snap.get("errors", 0)), DANGER),
            ("Elapsed", f"{elapsed:.0f}s", MUTED),
        ]:
            row = QHBoxLayout()
            ll = QLabel(label)
            ll.setFixedWidth(140)
            ll.setStyleSheet(f"color: {MUTED}; font-size: 13px;")
            row.addWidget(ll)
            vl = QLabel(value)
            vl.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 13px;")
            row.addWidget(vl)
            row.addStretch()
            cl.addLayout(row)
        lay.addWidget(card)

        info = QLabel(f"Results saved to {RESULTS_DIR / 'hits.txt'}")
        info.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        lay.addWidget(info)
        lay.addStretch()

        bl = QHBoxLayout()
        new_btn = QPushButton("New Check")
        new_btn.clicked.connect(self._show_wizard)
        bl.addWidget(new_btn)
        exit_btn = QPushButton("Exit")
        exit_btn.setObjectName("ghost")
        exit_btn.clicked.connect(self.close)
        bl.addWidget(exit_btn)
        bl.addStretch()
        lay.addLayout(bl)

        self._stack.addWidget(page)
        self._stack.setCurrentWidget(page)

    def closeEvent(self, event):
        self._stop_event.set()
        self._async.stop()
        event.accept()

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
                base = PROJECT_ROOT
                candidates.append(base / "ew2.ico")
                candidates.append(base / "ew2_icon.png")
            for icon_path in candidates:
                if icon_path.exists():
                    icon = QIcon(str(icon_path))
                    self.setWindowIcon(icon)
                    QApplication.instance().setWindowIcon(icon)
                    return
        except Exception:
            pass


def main():
    if not HAS_PYSIDE6:
        raise RuntimeError(
            "PySide6 is not installed. Install with:\n"
            "  pip install PySide6\n"
            "Then retry, or use --terminal mode."
        )
    ensure_dir(DATA_DIR, LOGS_DIR, RESULTS_DIR)
    ensure_file(DATA_DIR / "config.json")
    ensure_file(DATA_DIR / "names_to_check.txt")
    ensure_file(LOGS_DIR / "error.txt", clean=True)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = App()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
