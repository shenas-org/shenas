"""Per-user encryption key derivation and optional keyring persistence."""

from __future__ import annotations

import contextlib
import hashlib
import os

_KEYRING_SERVICE = "shenas"


def gen_salt() -> str:
    """Generate a fresh 16-byte salt as a hex string."""
    return os.urandom(16).hex()


def derive_user_key(password: str, salt: str) -> str:
    """Derive a 256-bit DuckDB encryption key from a password + salt via scrypt."""
    dk = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1, dklen=32)
    return dk.hex()


def _kr_user(user_id: int) -> str:
    return f"user_key_{user_id}"


def remember_user_key(user_id: int, key: str) -> None:
    """Persist a derived user key in the OS keyring (opt-in)."""
    import keyring

    with contextlib.suppress(Exception):
        keyring.delete_password(_KEYRING_SERVICE, _kr_user(user_id))
    keyring.set_password(_KEYRING_SERVICE, _kr_user(user_id), key)


def forget_user_key(user_id: int) -> None:
    """Remove a remembered user key from the OS keyring."""
    import keyring

    with contextlib.suppress(Exception):
        keyring.delete_password(_KEYRING_SERVICE, _kr_user(user_id))


def get_remembered_user_key(user_id: int) -> str | None:
    """Return the remembered key for a user, or None if not stored."""
    import keyring

    try:
        return keyring.get_password(_KEYRING_SERVICE, _kr_user(user_id))
    except Exception:
        return None
