#!/usr/bin/env python3
"""ew² – Crypto layer (delegates to security.py for maximum protection)."""

from __future__ import annotations

import warnings as _warnings

_warnings.warn(
    "crypto.py is deprecated. Import from 'security' directly instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Import everything from security.py — single source of truth
from security import (
    get_hwid,
    generate_token,
    hash_token,
    verify_token,
    is_creator_token,
    save_encrypted,
    load_encrypted,
    save_auth,
    load_auth,
    token_in_store,
    add_token_hash,
    save_session,
    load_session,
    ensure_creator,
    compute_integrity,
    verify_integrity,
    security_init,
    anti_debug,
    anti_vm,
    anti_extraction,
    save_activation,
    load_activation,
    is_machine_activated,
    is_token_consumed,
    consume_token,
    remove_activation,
)
