"""Per-user encryption key derivation."""

from __future__ import annotations

import hashlib
import os


def gen_salt() -> str:
    """Generate a fresh 16-byte salt as a hex string."""
    return os.urandom(16).hex()


def derive_user_key(password: str, salt: str) -> str:
    """Derive a 256-bit DuckDB encryption key from a password + salt via scrypt."""
    dk = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1, dklen=32)
    return dk.hex()
