"""Centralized DuckDB connection with encryption at rest.

Single shared connection for all reads, writes, and pipeline flushes.
Serialized via a threading RLock. Pipeline data flows from dlt's
in-memory connection through Arrow table registration into the
encrypted database -- no second file ATTACH needed.
"""

from __future__ import annotations

import contextlib
import os
import secrets
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

import duckdb

if TYPE_CHECKING:
    from collections.abc import Generator


def _resolve_db_path() -> Path:
    """Resolve database path. Uses ~/.shenas/data/ in PyInstaller bundles."""
    import sys

    if getattr(sys, "_MEIPASS", None):
        return Path.home() / ".shenas" / "data" / "shenas.duckdb"
    return Path("data") / "shenas.duckdb"


DB_PATH = _resolve_db_path()


_con: duckdb.DuckDBPyConnection | None = None
_lock = threading.RLock()


@contextlib.contextmanager
def cursor() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Get a cursor on the shared connection with USE db set."""
    con = connect()
    cur = con.cursor()
    try:
        cur.execute("USE db")
        yield cur
    finally:
        cur.close()


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

    with contextlib.suppress(Exception):
        keyring.delete_password("shenas", "db_key")
    keyring.set_password("shenas", "db_key", key)


def generate_db_key() -> str:
    """Generate a random 256-bit key as a hex string."""
    return secrets.token_hex(32)


def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:  # noqa: ARG001
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
            _ensure_system_tables(_con)
        return _con


def analytics_backend() -> Any:
    """Return an Ibis Backend wrapping a child cursor of the shared connection.

    Used by the analytics runner (``shenas_plugins.core.analytics.runner``)
    to compile + execute LLM-authored recipes against the encrypted DB
    via Ibis. Each call returns a fresh child cursor, so concurrent
    analytics runs don't step on each other.

    **Soft-guarantee read-only**: the underlying connection is the same
    read-write one used by syncs and writes. The "read-only" property
    comes from the fact that the analytics layer (operations + recipe
    compiler) only emits SELECT-shaped Ibis expressions; no INSERT /
    UPDATE / DELETE / DDL flows through this path. A future hardening
    pass (Phase 4) can enforce this at the connection level by spawning
    a separate read-only DuckDB process or using ``con.interrupt()`` to
    cancel runaway queries.
    """
    import ibis

    parent = connect()
    cur = parent.cursor()
    cur.execute("USE db")
    return ibis.duckdb.from_connection(cur)


def _ensure_system_tables(con: duckdb.DuckDBPyConnection) -> None:
    """Create system tables and canonical schema tables if they don't exist."""
    from app.hotkeys import Hotkey
    from app.hypotheses import Hypothesis
    from app.transforms import Transform
    from app.workspace import Workspace
    from shenas_plugins.core.plugin import Plugin
    from shenas_plugins.core.table import Table

    con.execute("CREATE SEQUENCE IF NOT EXISTS shenas_system.transform_seq START 1")
    con.execute("CREATE SEQUENCE IF NOT EXISTS shenas_system.hypothesis_seq START 1")
    tables = [Transform, Plugin._Table, Workspace, Hotkey._Table, Hypothesis]
    Table.ensure_schema(con, tables, schema="shenas_system")
    Hotkey.seed(con)
    from shenas_datasets.core.dataset import Dataset

    Dataset.ensure_all(con)


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

        all_schemas = [r[0] for r in mem_con.execute("SELECT schema_name FROM information_schema.schemata").fetchall()]
        schemas_to_copy = [s for s in all_schemas if s in (dataset_name, f"{dataset_name}_staging")]

        for schema in schemas_to_copy:
            server_con.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
            tables = mem_con.execute(
                "SELECT table_name FROM information_schema.tables"
                f" WHERE table_schema = '{schema}' AND table_catalog = 'memory'"
            ).fetchall()
            for (table_name,) in tables:
                tmp_name = f"_flush_{schema}_{table_name}".replace("-", "_")
                arrow_tbl = mem_con.execute(f'SELECT * FROM memory."{schema}"."{table_name}"').arrow()
                server_con.register(tmp_name, arrow_tbl)
                server_con.execute(f'CREATE OR REPLACE TABLE "{schema}"."{table_name}" AS SELECT * FROM {tmp_name}')
                server_con.unregister(tmp_name)

    mem_con.close()
