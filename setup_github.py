#!/usr/bin/env python3
"""ew² – GitHub setup tool. Creates repo structure and encrypts URL."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
import subprocess
import uuid
from pathlib import Path

# ── HWID ────────────────────────────────────────────────────────────────────
def _hwid() -> str:
    parts = [platform.node(), platform.machine(), platform.processor(), str(uuid.getnode())]
    try:
        r = subprocess.run(["wmic", "baseboard", "get", "serialnumber"],
                           capture_output=True, text=True, timeout=5)
        for line in r.stdout.splitlines():
            s = line.strip()
            if s and s != "SerialNumber":
                parts.append(s)
                break
    except Exception:
        pass
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:24]


def _xor(data: bytes, key: bytes) -> bytes:
    klen = len(key)
    return bytes(b ^ key[i % klen] for i, b in enumerate(data))


def _derive_key() -> bytes:
    return hashlib.pbkdf2_hmac("sha256", _hwid().encode(), b"ew2-salt-v1", 100_000, dklen=32)


def encrypt_url(url: str) -> str:
    key = _derive_key()
    encrypted = _xor(url.encode(), key)
    return base64.b64encode(encrypted).decode()


def decrypt_url(encrypted_b64: str) -> str:
    key = _derive_key()
    encrypted = base64.b64decode(encrypted_b64)
    return _xor(encrypted, key).decode()


# ── Repo structure ──────────────────────────────────────────────────────────
SAMPLE_CONFIG = {
    "webhook": "",
    "webhook_message": "**<name>** available | <t:time:R>",
    "webhook_always": False,
}

SAMPLE_NAMES = """admin
test
user
guest
root
support
help
info
contact
demo"""


def create_repo_files(repo_path: Path) -> None:
    """Create the files that should be in the GitHub repo."""
    repo_path.mkdir(parents=True, exist_ok=True)

    (repo_path / "config.json").write_text(
        json.dumps(SAMPLE_CONFIG, indent=2), encoding="utf-8"
    )
    (repo_path / "names_to_check.txt").write_text(
        SAMPLE_NAMES.strip(), encoding="utf-8"
    )
    (repo_path / "proxies.txt").write_text("", encoding="utf-8")

    print(f"\n  Repo files created at: {repo_path}")
    print(f"\n  Upload these to your GitHub repo:")
    print(f"    - config.json")
    print(f"    - names_to_check.txt")
    print(f"    - proxies.txt")


# ── Main ────────────────────────────────────────────────────────────────────
def main() -> None:
    print(f"\n  ew² GitHub Setup")
    print(f"  Your HWID: {_hwid()}\n")

    print("  [1] Create repo files locally")
    print("  [2] Encrypt GitHub URL")
    print("  [3] Decrypt and test URL")
    print("  [4] Exit\n")

    choice = input("  Choice: ").strip()

    if choice == "1":
        path = input("  Path to create repo files: ").strip() or "ew2-repo"
        create_repo_files(Path(path))

    elif choice == "2":
        url = input("  GitHub raw URL: ").strip()
        if not url.startswith("http"):
            print("  Invalid URL")
            return
        encrypted = encrypt_url(url)
        print(f"\n  Encrypted URL (paste in github_loader.py as _GITHUB_URL_B64):")
        print(f'  _GITHUB_URL_B64 = "{encrypted}"')
        print(f"\n  Test decrypt: {decrypt_url(encrypted)}")

    elif choice == "3":
        encrypted = input("  Paste encrypted URL: ").strip()
        try:
            result = decrypt_url(encrypted)
            print(f"\n  Decrypted: {result}")
        except Exception as e:
            print(f"\n  Error: {e}")

    elif choice == "4":
        return


if __name__ == "__main__":
    main()
