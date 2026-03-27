"""Database connection for pipes with encryption at rest."""

import os
from pathlib import Path
from typing import Any

import duckdb

DB_PATH = Path("data") / "shenas.duckdb"

_active_con: duckdb.DuckDBPyConnection | None = None


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


def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Connect to the encrypted DuckDB database. Reuses active connection if available."""
    global _active_con
    if _active_con is not None:
        return _active_con

    key = get_db_key()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    ro = ", READ_ONLY true" if read_only else ""
    con.execute(f"ATTACH '{DB_PATH}' AS db (ENCRYPTION_KEY '{key}'{ro})")
    con.execute("USE db")
    _active_con = con
    return con


def close() -> None:
    """Close and release the active connection."""
    global _active_con
    if _active_con is not None:
        _active_con.close()
        _active_con = None


def dlt_destination() -> Any:
    """Return a dlt DuckDB destination using an encrypted connection."""
    import dlt

    return dlt.destinations.duckdb(credentials=connect())
