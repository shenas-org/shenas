"""Centralized DuckDB connection with encryption at rest.

Single shared connection for all reads, writes, and pipeline flushes.
Serialized via a threading RLock. Pipeline data flows from dlt's
in-memory connection through Arrow table registration into the
encrypted database -- no second file ATTACH needed.
"""

from __future__ import annotations

import os
import secrets
import threading
from pathlib import Path
from typing import Any

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


def dlt_destination() -> tuple[Any, duckdb.DuckDBPyConnection]:
    """Return a dlt DuckDB destination backed by an in-memory connection.

    dlt writes to memory (nothing on disk unencrypted). After pipeline.run(),
    call flush_from_memory() to copy the data into the encrypted DB.
    """
    import dlt

    mem_con = duckdb.connect(":memory:")
    return dlt.destinations.duckdb(credentials=mem_con), mem_con


def flush_from_memory(mem_con: duckdb.DuckDBPyConnection, dataset_name: str) -> None:
    """Copy tables from an in-memory dlt connection into the encrypted DB.

    Uses Arrow table registration to transfer data through the server's
    existing connection. No second ATTACH needed -- avoids file lock conflicts.
    """
    with _lock:
        server_con = connect()

        schemas_to_copy = []
        all_schemas = [r[0] for r in mem_con.execute("SELECT schema_name FROM information_schema.schemata").fetchall()]
        for s in all_schemas:
            if s in (dataset_name, f"{dataset_name}_staging"):
                schemas_to_copy.append(s)

        for schema in schemas_to_copy:
            server_con.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
            tables = mem_con.execute(
                f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{schema}' AND table_catalog = 'memory'"
            ).fetchall()
            for (table_name,) in tables:
                tmp_name = f"_flush_{schema}_{table_name}"
                arrow_tbl = mem_con.execute(f"SELECT * FROM memory.{schema}.{table_name}").arrow()
                server_con.register(tmp_name, arrow_tbl)
                server_con.execute(f"CREATE OR REPLACE TABLE {schema}.{table_name} AS SELECT * FROM {tmp_name}")
                server_con.unregister(tmp_name)

    mem_con.close()
