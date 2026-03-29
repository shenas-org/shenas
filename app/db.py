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
    For concurrent queries, use con.cursor() to get a per-request cursor.
    """
    global _con
    with _lock:
        if _con is None:
            key = get_db_key()
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            _con = duckdb.connect()
            _con.execute(f"ATTACH '{DB_PATH}' AS db (ENCRYPTION_KEY '{key}')")
            _con.execute("USE db")
            _ensure_plugin_table(_con)
        return _con


def _ensure_plugin_table(con: duckdb.DuckDBPyConnection) -> None:
    """Create the plugin state table if it doesn't exist.

    Uses CREATE TABLE IF NOT EXISTS + ADD COLUMN for new columns.
    Old columns are left in place (harmless, never queried).
    """
    con.execute("CREATE SCHEMA IF NOT EXISTS shenas_system")
    con.execute("""
        CREATE TABLE IF NOT EXISTS shenas_system.plugins (
            kind VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            added_at TIMESTAMP DEFAULT current_timestamp,
            updated_at TIMESTAMP,
            status_changed_at TIMESTAMP,
            PRIMARY KEY (kind, name)
        )
    """)
    # Add status_changed_at if missing (table may predate this column)
    cols = {
        r[0]
        for r in con.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'shenas_system' AND table_name = 'plugins'"
        ).fetchall()
    }
    if "status_changed_at" not in cols:
        con.execute("ALTER TABLE shenas_system.plugins ADD COLUMN status_changed_at TIMESTAMP")


def get_plugin_state(kind: str, name: str) -> dict[str, Any] | None:
    """Get plugin state from the DB. Returns None if not tracked."""
    con = connect()
    cur = con.cursor()
    cur.execute("USE db")
    row = cur.execute(
        "SELECT kind, name, enabled, added_at, updated_at, status_changed_at "
        "FROM shenas_system.plugins WHERE kind = ? AND name = ?",
        [kind, name],
    ).fetchone()
    cur.close()
    if not row:
        return None
    return {
        "kind": row[0],
        "name": row[1],
        "enabled": row[2],
        "added_at": str(row[3]) if row[3] else None,
        "updated_at": str(row[4]) if row[4] else None,
        "status_changed_at": str(row[5]) if row[5] else None,
    }


def get_all_plugin_states(kind: str | None = None) -> list[dict[str, Any]]:
    """Get all tracked plugin states, optionally filtered by kind."""
    con = connect()
    cur = con.cursor()
    cur.execute("USE db")
    if kind:
        rows = cur.execute(
            "SELECT kind, name, enabled, added_at, updated_at, status_changed_at "
            "FROM shenas_system.plugins WHERE kind = ? ORDER BY name",
            [kind],
        ).fetchall()
    else:
        rows = cur.execute(
            "SELECT kind, name, enabled, added_at, updated_at, status_changed_at "
            "FROM shenas_system.plugins ORDER BY kind, name"
        ).fetchall()
    cur.close()
    return [
        {
            "kind": r[0],
            "name": r[1],
            "enabled": r[2],
            "added_at": str(r[3]) if r[3] else None,
            "updated_at": str(r[4]) if r[4] else None,
            "status_changed_at": str(r[5]) if r[5] else None,
        }
        for r in rows
    ]


def upsert_plugin_state(kind: str, name: str, enabled: bool = True) -> None:
    """Insert or update plugin state with current timestamp."""
    con = connect()
    existing = get_plugin_state(kind, name)
    now = "current_timestamp"
    if existing:
        if enabled != existing["enabled"]:
            con.execute(
                f"UPDATE shenas_system.plugins SET enabled = ?, status_changed_at = {now}, updated_at = {now} "
                "WHERE kind = ? AND name = ?",
                [enabled, kind, name],
            )
        else:
            con.execute(
                f"UPDATE shenas_system.plugins SET updated_at = {now} WHERE kind = ? AND name = ?",
                [kind, name],
            )
    else:
        con.execute(
            f"INSERT INTO shenas_system.plugins (kind, name, enabled, added_at, status_changed_at) "
            f"VALUES (?, ?, ?, {now}, {now})",
            [kind, name, enabled],
        )


def remove_plugin_state(kind: str, name: str) -> None:
    """Remove plugin state from the DB."""
    con = connect()
    con.execute("DELETE FROM shenas_system.plugins WHERE kind = ? AND name = ?", [kind, name])


def is_plugin_enabled(kind: str, name: str) -> bool:
    """Check if a plugin is enabled. Returns True if not tracked (default enabled)."""
    state = get_plugin_state(kind, name)
    if state is None:
        return True
    return state["enabled"]


def dlt_destination() -> tuple[Any, duckdb.DuckDBPyConnection]:
    """Return a dlt DuckDB destination backed by an in-memory connection.

    dlt writes to memory (nothing on disk unencrypted). After pipeline.run(),
    call flush_to_encrypted() to copy the data into the encrypted DB.
    """
    import dlt

    mem_con = duckdb.connect(":memory:")
    return dlt.destinations.duckdb(credentials=mem_con), mem_con


def flush_to_encrypted(mem_con: duckdb.DuckDBPyConnection, dataset_name: str) -> None:
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
            server_con.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
            tables = mem_con.execute(
                f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{schema}' AND table_catalog = 'memory'"
            ).fetchall()
            for (table_name,) in tables:
                tmp_name = f"_flush_{schema}_{table_name}".replace("-", "_")
                arrow_tbl = mem_con.execute(f'SELECT * FROM memory."{schema}"."{table_name}"').arrow()
                server_con.register(tmp_name, arrow_tbl)
                server_con.execute(f'CREATE OR REPLACE TABLE "{schema}"."{table_name}" AS SELECT * FROM {tmp_name}')
                server_con.unregister(tmp_name)

    mem_con.close()
