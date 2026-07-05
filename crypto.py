#!/usr/bin/env python3
"""Klatom – Encrypted auth + HWID + token hashing (HARDENED)."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import platform
import subprocess
import sys
import time
import uuid
from pathlib import Path

_ENC_SALT = b"\xa3\x8f\x1b\xd4\x6e\x2c\x9a\x07\xf5\x12\x8b\x3d\xc6\x4e\x70\xa1"
_HMAC_KEY = b"\x71\xdc\x3f\x92\xb8\x54\xe6\x0a\x1d\x47\xcf\x83\x6b\x29\xf0\x55"
_TOKEN_SECRET = b"\xe9\x4a\x17\xd3\x6f\x82\xbc\x05\x3d\x91\x7e\x46\xab\x28\xcf\x50"
_KDF_ITERS = 500_000

_debugger_detected = False

def _check_debugger() -> bool:
    global _debugger_detected
    if _debugger_detected:
        return True
    try:
        for env in ("PYDEVD", "PYCHARM_DEBUG", "REMOTE_DEBUG", "DEBUGPY_RUNNING"):
            if os.environ.get(env):
                _debugger_detected = True
                return True
        if platform.system() == "Windows":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                if kernel32.IsDebuggerPresent():
                    _debugger_detected = True
                    return True
            except Exception:
                pass
    except Exception:
        pass
    return False

_integrity_hash: str | None = None

def _compute_integrity() -> str:
    global _integrity_hash
    if _integrity_hash:
        return _integrity_hash
    try:
        if getattr(sys, 'frozen', False):
            exe_path = Path(sys.executable)
        else:
            exe_path = Path(__file__)
        h = hashlib.sha256()
        with open(exe_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        _integrity_hash = h.hexdigest()[:32]
    except Exception:
        _integrity_hash = "no-integrity"
    return _integrity_hash


def get_hwid() -> str:
    try:
        parts = [platform.node(), platform.machine(), platform.processor(), str(uuid.getnode())]
        for cmd, field in [
            (["wmic", "baseboard", "get", "serialnumber"], "SerialNumber"),
            (["wmic", "diskdrive", "get", "serialnumber"], "SerialNumber"),
            (["wmic", "bios", "get", "serialnumber"], "SerialNumber"),
        ]:
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                for line in r.stdout.splitlines():
                    s = line.strip()
                    if s and s != field:
                        parts.append(s)
                        break
            except Exception:
                pass
        return hashlib.sha256("|".join(parts).encode()).hexdigest()[:24]
    except Exception:
        return "fallback-hwid"


def _derive_key(password: str) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), _ENC_SALT, _KDF_ITERS, dklen=32)


def _xor(data: bytes, key: bytes) -> bytes:
    klen = len(key)
    return bytes(b ^ key[i % klen] for i, b in enumerate(data))


def _hmac(data: bytes) -> str:
    return hmac.new(_HMAC_KEY, data, hashlib.sha256).hexdigest()


def save_encrypted(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data_with_meta = dict(data)
    data_with_meta["_t"] = int(time.time())
    data_with_meta["_i"] = _compute_integrity()
    plaintext = json.dumps(data_with_meta, separators=(",", ":")).encode()
    key = _derive_key(get_hwid())
    salt = os.urandom(16)
    cipher_key = hashlib.pbkdf2_hmac("sha256", key, salt, 3, dklen=32)
    encrypted = _xor(plaintext, cipher_key)
    payload = {"s": salt.hex(), "d": encrypted.hex(), "h": _hmac(plaintext), "v": 3}
    for attempt in range(3):
        try:
            tmp = path.with_suffix(f".tmp{attempt}")
            tmp.write_text(json.dumps(payload), encoding="utf-8")
            tmp.replace(path)
            return
        except Exception:
            if attempt == 2:
                try:
                    path.write_text(json.dumps(payload), encoding="utf-8")
                except Exception:
                    pass
            time.sleep(0.01)


def load_encrypted(path: Path) -> dict | None:
    if not path.exists():
        return None
    if _check_debugger():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        version = raw.get("v", 0)
        if version < 2:
            return None
        salt = bytes.fromhex(raw["s"])
        encrypted = bytes.fromhex(raw["d"])
        expected_hmac = raw["h"]
        key = _derive_key(get_hwid())
        cipher_key = hashlib.pbkdf2_hmac("sha256", key, salt, 3, dklen=32)
        plaintext = _xor(encrypted, cipher_key)
        if not hmac.compare_digest(_hmac(plaintext), expected_hmac):
            return None
        data = json.loads(plaintext)
        data.pop("_t", None)
        data.pop("_i", None)
        return data
    except Exception:
        return None


def generate_token() -> str:
    return f"KLATOM-{os.urandom(4).hex().upper()}-{os.urandom(4).hex().upper()}-{os.urandom(4).hex().upper()}"


def hash_token(token: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", token.upper().encode(), _TOKEN_SECRET, 100_000, dklen=32).hex()


def verify_token(token: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_token(token), stored_hash)


def is_creator_token(token: str) -> bool:
    return token.upper().strip() == "CREATOR"


def save_auth(auth_path: Path, token_hashes: list[str]) -> None:
    save_encrypted(auth_path, {"t": token_hashes, "v": 2})


def load_auth(auth_path: Path) -> dict | None:
    return load_encrypted(auth_path)


def token_in_store(token: str, auth_path: Path) -> bool:
    data = load_auth(auth_path)
    if data is None:
        return False
    return hash_token(token) in data.get("t", [])


def add_token_hash(auth_path: Path, token: str) -> None:
    data = load_auth(auth_path)
    if data is None:
        data = {"t": [], "v": 2}
    h = hash_token(token)
    if h not in data["t"]:
        data["t"].append(h)
    save_auth(auth_path, data["t"])


def save_session(session_path: Path, trial_start: float, hwid: str) -> None:
    save_encrypted(session_path, {"ts": trial_start, "th": hwid, "v": 1, "te": trial_start + 86400})


def load_session(session_path: Path) -> dict | None:
    return load_encrypted(session_path)


def ensure_creator(auth_path: Path) -> None:
    data = load_auth(auth_path)
    if data is None:
        save_auth(auth_path, [hash_token("CREATOR")])
