"""Centralized DuckDB connection with encryption at rest."""

import os
import secrets
from pathlib import Path

import duckdb

DB_PATH = Path("data") / "shenas.duckdb"


def get_db_key() -> str:
    """Get the database encryption key from env var or OS keyring."""
    key = os.environ.get("SHENAS_DB_KEY")
    if key:
        return key
    import keyring

    key = keyring.get_password("shenas", "db_key")
    if key:
        return key
    raise RuntimeError("No database key found. Run 'shenas db keygen' or set SHENAS_DB_KEY.")


def set_db_key(key: str) -> None:
    """Store the database encryption key in the OS keyring."""
    import keyring

    keyring.set_password("shenas", "db_key", key)


def generate_db_key() -> str:
    """Generate a random 256-bit key as a hex string."""
    return secrets.token_hex(32)


def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Connect to the encrypted DuckDB database."""
    key = get_db_key()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    ro = ", READ_ONLY true" if read_only else ""
    con.execute(f"ATTACH '{DB_PATH}' AS db (ENCRYPTION_KEY '{key}'{ro})")
    con.execute("USE db")
    return con
