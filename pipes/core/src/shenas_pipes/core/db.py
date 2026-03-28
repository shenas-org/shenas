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


def dlt_destination() -> tuple[Any, duckdb.DuckDBPyConnection]:
    """Return a dlt DuckDB destination backed by an in-memory connection.

    dlt writes to memory (nothing on disk unencrypted). After pipeline.run(),
    call flush_to_encrypted() to copy the data into the encrypted DB.
    """
    import dlt

    mem_con = duckdb.connect(":memory:")
    return dlt.destinations.duckdb(credentials=mem_con), mem_con


def flush_to_encrypted(mem_con: duckdb.DuckDBPyConnection, dataset_name: str) -> None:
    """Copy all tables from an in-memory dlt connection into the encrypted DB."""
    key = get_db_key()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    mem_con.execute(f"ATTACH '{DB_PATH}' AS enc (ENCRYPTION_KEY '{key}')")

    # Get all schemas written by dlt (dataset + staging)
    schemas_to_copy = []
    all_schemas = [r[0] for r in mem_con.execute("SELECT schema_name FROM information_schema.schemata").fetchall()]
    for s in all_schemas:
        if s in (dataset_name, f"{dataset_name}_staging"):
            schemas_to_copy.append(s)

    for schema in schemas_to_copy:
        mem_con.execute(f"CREATE SCHEMA IF NOT EXISTS enc.{schema}")
        tables = mem_con.execute(
            f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{schema}'"
        ).fetchall()
        for (table_name,) in tables:
            mem_con.execute(f"DROP TABLE IF EXISTS enc.{schema}.{table_name}")
            mem_con.execute(f"CREATE TABLE enc.{schema}.{table_name} AS SELECT * FROM {schema}.{table_name}")

    mem_con.execute("DETACH enc")
