#!/usr/bin/env python3
"""Klatom – Secure token generator (CREATOR ONLY, HWID-locked)."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import uuid
from pathlib import Path

# ── HWID (same as crypto.py) ───────────────────────────────────────────────
def _hwid() -> str:
    try:
        parts = [
            platform.node(), platform.machine(), platform.processor(),
            str(uuid.getnode()),
        ]
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
        try:
            r = subprocess.run(["wmic", "diskdrive", "get", "serialnumber"],
                               capture_output=True, text=True, timeout=5)
            for line in r.stdout.splitlines():
                s = line.strip()
                if s and s != "SerialNumber":
                    parts.append(s)
                    break
        except Exception:
            pass
        return hashlib.sha256("|".join(parts).encode()).hexdigest()[:24]
    except Exception:
        return "unknown"


# ── Creator HWID (yours — set once, never change) ──────────────────────────
CREATOR_HWID = "f30ed9a7f098b5ecdcfe8a07"

def _check_creator() -> bool:
    if not CREATOR_HWID:
        return True  # First run — allow setup
    return _hwid() == CREATOR_HWID


# ── Token generation ────────────────────────────────────────────────────────
def generate_token() -> str:
    import secrets
    return f"KLATOM-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"


# ── Token storage (plain text for distribution) ─────────────────────────────
_TOKENS_FILE = Path(__file__).parent / "data" / ".tokens"

def _load_tokens() -> list[str]:
    if _TOKENS_FILE.exists():
        try:
            return json.loads(_TOKENS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []

def _save_tokens(tokens: list[str]) -> None:
    _TOKENS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _TOKENS_FILE.write_text(json.dumps(tokens, indent=2), encoding="utf-8")


# ── Main ────────────────────────────────────────────────────────────────────
def main() -> None:
    hwid = _hwid()

    if not _check_creator():
        print(f"\n  [BLOCKED] This machine is not the creator.")
        print(f"  Your HWID: {hwid}")
        print(f"  Creator HWID: {CREATOR_HWID}")
        input("\n  Press Enter to exit...")
        return

    print(f"\n  Creator HWID: {hwid}")
    if not CREATOR_HWID:
        print(f"\n  First run detected. Set CREATOR_HWID to:")
        print(f'  CREATOR_HWID = "{hwid}"')
        print(f"  in this file, then run again.")
        input("\n  Press Enter to exit...")
        return

    tokens = _load_tokens()
    print(f"  Active tokens: {len(tokens)}\n")

    while True:
        print("  [1] Generate token")
        print("  [2] Generate multiple")
        print("  [3] List tokens")
        print("  [4] Revoke token")
        print("  [5] Exit")

        choice = input("\n  Choice: ").strip()

        if choice == "1":
            tok = generate_token()
            tokens.append(tok)
            _save_tokens(tokens)
            print(f"\n  Generated: {tok}")
            print(f"  Total: {len(tokens)}\n")

        elif choice == "2":
            try:
                count = int(input("  How many: ").strip())
            except ValueError:
                count = 1
            new = [generate_token() for _ in range(count)]
            tokens.extend(new)
            _save_tokens(tokens)
            print(f"\n  Generated {count} tokens:")
            for t in new:
                print(f"    {t}")
            print(f"  Total: {len(tokens)}\n")

        elif choice == "3":
            if not tokens:
                print("\n  No tokens.\n")
            else:
                print(f"\n  Tokens ({len(tokens)}):")
                for i, t in enumerate(tokens, 1):
                    print(f"    {i}. {t}")
                print()

        elif choice == "4":
            tok = input("  Token to revoke: ").strip()
            if tok in tokens:
                tokens.remove(tok)
                _save_tokens(tokens)
                print(f"\n  Revoked. Total: {len(tokens)}\n")
            else:
                print("\n  Not found.\n")

        elif choice == "5":
            break


if __name__ == "__main__":
    main()
