"""Database connection for pipes — delegates to cli.db."""

import os
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


def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Connect to the encrypted DuckDB database."""
    key = get_db_key()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    ro = ", READ_ONLY true" if read_only else ""
    con.execute(f"ATTACH '{DB_PATH}' AS db (ENCRYPTION_KEY '{key}'{ro})")
    con.execute("USE db")
    return con


def get_dlt_credentials() -> str:
    """Return a dlt-compatible DuckDB credentials string.

    For encrypted databases, dlt needs to connect through our connect() function.
    This returns the DB path as a string — dlt pipelines should use a custom connection.
    """
    return str(DB_PATH)
