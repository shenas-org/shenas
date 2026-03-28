"""Centralized DuckDB connection with encryption at rest.

Uses a single shared connection for all reads and writes, serialized
via a threading lock. The connection is closed and recreated when
exclusive file access is needed (e.g. flush_to_encrypted).
"""

import os
import secrets
import threading
from pathlib import Path

import duckdb

DB_PATH = Path("data") / "shenas.duckdb"

_con: duckdb.DuckDBPyConnection | None = None
_lock = threading.RLock()


def get_db_key() -> str:
    """Get the database encryption key from env var or OS keyring."""
    key = os.environ.get("SHENAS_DB_KEY")
    if key:
        return key
    import keyring

    key = keyring.get_password("shenas", "db_key")
    if key:
        return key
    raise RuntimeError("No database key found. Run 'shenasctl db keygen' or set SHENAS_DB_KEY.")


def set_db_key(key: str) -> None:
    """Store the database encryption key in the OS keyring."""
    import keyring

    try:
        keyring.delete_password("shenas", "db_key")
    except Exception:
        pass
    keyring.set_password("shenas", "db_key", key)


def generate_db_key() -> str:
    """Generate a random 256-bit key as a hex string."""
    return secrets.token_hex(32)


def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Get the shared DuckDB connection.

    Uses a single long-lived connection for all operations.
    The read_only parameter is accepted for API compatibility but ignored --
    all operations use the same read-write connection.

    Callers should NOT close the returned connection.
    """
    global _con
    with _lock:
        if _con is None:
            key = get_db_key()
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            _con = duckdb.connect()
            _con.execute(f"ATTACH '{DB_PATH}' AS db (ENCRYPTION_KEY '{key}')")
            _con.execute("USE db")
        return _con


def close_all() -> None:
    """Close the shared connection and release the file lock.

    Called before operations that need exclusive file access from
    a different connection (e.g. flush_to_encrypted).
    The connection is lazily recreated on next use.
    """
    global _con
    with _lock:
        if _con is not None:
            _con.close()
            _con = None
