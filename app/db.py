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

DB_PATH = Path("data") / "shenas.duckdb"

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


def _ensure_system_tables(con: duckdb.DuckDBPyConnection) -> None:
    """Create system tables if they don't exist."""
    con.execute("CREATE SCHEMA IF NOT EXISTS shenas_system")
    _ensure_plugin_table(con)
    _ensure_transforms_table(con)
    _ensure_workspace_table(con)
    _ensure_hotkeys_table(con)


def _ensure_transforms_table(con: duckdb.DuckDBPyConnection) -> None:
    """Create the transforms table."""
    con.execute("CREATE SEQUENCE IF NOT EXISTS shenas_system.transform_seq START 1")
    con.execute("""
        CREATE TABLE IF NOT EXISTS shenas_system.transforms (
            id INTEGER PRIMARY KEY DEFAULT nextval('shenas_system.transform_seq'),
            source_duckdb_schema VARCHAR NOT NULL,
            source_duckdb_table VARCHAR NOT NULL,
            target_duckdb_schema VARCHAR NOT NULL,
            target_duckdb_table VARCHAR NOT NULL,
            source_plugin VARCHAR NOT NULL,
            description VARCHAR DEFAULT '',
            sql TEXT NOT NULL,
            is_default BOOLEAN DEFAULT FALSE,
            enabled BOOLEAN DEFAULT TRUE,
            added_at TIMESTAMP DEFAULT current_timestamp,
            updated_at TIMESTAMP,
            status_changed_at TIMESTAMP
        )
    """)
    # Add description if missing (table may predate this column)
    cols = {
        r[0]
        for r in con.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'shenas_system' AND table_name = 'transforms'"
        ).fetchall()
    }
    if "description" not in cols:
        con.execute("ALTER TABLE shenas_system.transforms ADD COLUMN description VARCHAR DEFAULT ''")


def _ensure_plugin_table(con: duckdb.DuckDBPyConnection) -> None:
    """Create the plugin state table if it doesn't exist."""
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
    if "synced_at" not in cols:
        con.execute("ALTER TABLE shenas_system.plugins ADD COLUMN synced_at TIMESTAMP")


def get_plugin_state(kind: str, name: str) -> dict[str, Any] | None:
    """Get plugin state from the DB. Returns None if not tracked."""
    con = connect()
    cur = con.cursor()
    cur.execute("USE db")
    row = cur.execute(
        "SELECT kind, name, enabled, added_at, updated_at, status_changed_at, synced_at "
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
        "synced_at": str(row[6]) if row[6] else None,
    }


def get_all_plugin_states(kind: str | None = None) -> list[dict[str, Any]]:
    """Get all tracked plugin states, optionally filtered by kind."""
    con = connect()
    cur = con.cursor()
    cur.execute("USE db")
    if kind:
        rows = cur.execute(
            "SELECT kind, name, enabled, added_at, updated_at, status_changed_at, synced_at "
            "FROM shenas_system.plugins WHERE kind = ? ORDER BY name",
            [kind],
        ).fetchall()
    else:
        rows = cur.execute(
            "SELECT kind, name, enabled, added_at, updated_at, status_changed_at, synced_at "
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
            "synced_at": str(r[6]) if r[6] else None,
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


def update_synced_at(kind: str, name: str) -> None:
    """Update the synced_at timestamp for a plugin. Creates the row if missing."""
    existing = get_plugin_state(kind, name)
    if not existing:
        upsert_plugin_state(kind, name, enabled=True)
    con = connect()
    con.execute(
        "UPDATE shenas_system.plugins SET synced_at = current_timestamp, updated_at = current_timestamp "
        "WHERE kind = ? AND name = ?",
        [kind, name],
    )


def _pipe_config_tables_with_frequency(cur: duckdb.DuckDBPyConnection) -> list[tuple[str, str]]:
    """Return (qualified_table, pipe_name) pairs for config tables that have a sync_frequency column."""
    rows = cur.execute("""
        SELECT table_schema, table_name
        FROM information_schema.columns
        WHERE column_name = 'sync_frequency'
          AND table_schema = 'config'
          AND table_name LIKE 'pipe_%'
    """).fetchall()
    return [(f'config."{r[1]}"', r[1][len("pipe_") :]) for r in rows]


def get_pipes_due_for_sync() -> list[dict[str, Any]]:
    """Return pipes whose sync frequency has elapsed since last sync."""
    con = connect()
    cur = con.cursor()
    cur.execute("USE db")
    tables = _pipe_config_tables_with_frequency(cur)
    if not tables:
        cur.close()
        return []

    union_parts = [
        # id = 1 is the single config row each pipe creates on first run; pipes with no
        # config row yet are silently excluded (they have no frequency to check anyway).
        f"SELECT '{pipe_name}' AS pipe_name, sync_frequency FROM {tbl} WHERE id = 1 AND sync_frequency IS NOT NULL"
        for tbl, pipe_name in tables
    ]
    union_sql = " UNION ALL ".join(union_parts)

    rows = cur.execute(f"""
        SELECT cfg.pipe_name, p.synced_at, cfg.sync_frequency
        FROM ({union_sql}) cfg
        JOIN shenas_system.plugins p ON p.kind = 'pipe' AND p.name = cfg.pipe_name
        WHERE p.enabled = TRUE
          AND (p.synced_at IS NULL
               OR p.synced_at + (cfg.sync_frequency * INTERVAL '1 minute') <= current_timestamp)
        ORDER BY cfg.pipe_name
    """).fetchall()
    cur.close()
    return [
        {
            "name": r[0],
            "synced_at": str(r[1]) if r[1] else None,
            "sync_frequency": r[2],
        }
        for r in rows
    ]


def get_all_sync_schedules() -> list[dict[str, Any]]:
    """Return all pipes with sync_frequency set, with their due status."""
    con = connect()
    cur = con.cursor()
    cur.execute("USE db")
    tables = _pipe_config_tables_with_frequency(cur)
    if not tables:
        cur.close()
        return []

    union_parts = [
        # id = 1 is the single config row each pipe creates on first run; pipes with no
        # config row yet are silently excluded (they have no frequency to check anyway).
        f"SELECT '{pipe_name}' AS pipe_name, sync_frequency FROM {tbl} WHERE id = 1 AND sync_frequency IS NOT NULL"
        for tbl, pipe_name in tables
    ]
    union_sql = " UNION ALL ".join(union_parts)

    rows = cur.execute(f"""
        SELECT cfg.pipe_name, p.synced_at, cfg.sync_frequency,
               CASE WHEN p.synced_at IS NULL
                    OR p.synced_at + (cfg.sync_frequency * INTERVAL '1 minute') <= current_timestamp
                    THEN TRUE ELSE FALSE END AS is_due
        FROM ({union_sql}) cfg
        JOIN shenas_system.plugins p ON p.kind = 'pipe' AND p.name = cfg.pipe_name
        WHERE p.enabled = TRUE
        ORDER BY cfg.pipe_name
    """).fetchall()
    cur.close()
    return [
        {
            "name": r[0],
            "synced_at": str(r[1]) if r[1] else None,
            "sync_frequency": r[2],
            "is_due": r[3],
        }
        for r in rows
    ]


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


def _ensure_workspace_table(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("""
        CREATE TABLE IF NOT EXISTS shenas_system.workspace (
            id INTEGER PRIMARY KEY DEFAULT 1,
            state VARCHAR NOT NULL DEFAULT '{}',
            updated_at TIMESTAMP DEFAULT current_timestamp
        )
    """)


def get_workspace() -> dict[str, Any]:
    """Get the workspace state. Returns empty dict if not set."""
    import json

    cur = connect().cursor()
    cur.execute("USE db")
    row = cur.execute("SELECT state FROM shenas_system.workspace WHERE id = 1").fetchone()
    cur.close()
    if not row:
        return {}
    try:
        return json.loads(row[0])
    except Exception:
        return {}


def save_workspace(state: dict[str, Any]) -> None:
    """Save the workspace state (atomic upsert)."""
    import json

    data = json.dumps(state)
    con = connect()
    con.execute(
        "INSERT INTO shenas_system.workspace (id, state, updated_at) VALUES (1, ?, now()) "
        "ON CONFLICT (id) DO UPDATE SET state = excluded.state, updated_at = now()",
        [data],
    )


_DEFAULT_HOTKEYS = [
    ("command-palette", "Ctrl+P"),
    ("navigation-palette", "Ctrl+O"),
    ("close-tab", "Ctrl+W"),
    ("new-tab", "Ctrl+T"),
]


def _ensure_hotkeys_table(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("""
        CREATE TABLE IF NOT EXISTS shenas_system.hotkeys (
            action_id VARCHAR PRIMARY KEY,
            binding VARCHAR NOT NULL DEFAULT '',
            updated_at TIMESTAMP DEFAULT current_timestamp
        )
    """)
    row = con.execute("SELECT COUNT(*) FROM shenas_system.hotkeys").fetchone()
    if row and row[0] == 0:
        for action_id, binding in _DEFAULT_HOTKEYS:
            con.execute(
                "INSERT INTO shenas_system.hotkeys (action_id, binding) VALUES (?, ?)",
                [action_id, binding],
            )


def get_hotkeys() -> dict[str, str]:
    """Get all hotkey bindings as {action_id: binding}."""
    cur = connect().cursor()
    cur.execute("USE db")
    rows = cur.execute("SELECT action_id, binding FROM shenas_system.hotkeys ORDER BY action_id").fetchall()
    cur.close()
    return {r[0]: r[1] for r in rows}


def set_hotkey(action_id: str, binding: str) -> None:
    """Set a single hotkey binding (upsert)."""
    con = connect()
    con.execute(
        "INSERT INTO shenas_system.hotkeys (action_id, binding, updated_at) VALUES (?, ?, current_timestamp) "
        "ON CONFLICT (action_id) DO UPDATE SET binding = ?, updated_at = current_timestamp",
        [action_id, binding, binding],
    )


def delete_hotkey(action_id: str) -> None:
    """Remove a hotkey binding."""
    con = connect()
    con.execute("DELETE FROM shenas_system.hotkeys WHERE action_id = ?", [action_id])


def reset_hotkeys() -> None:
    """Reset hotkeys to defaults."""
    con = connect()
    con.execute("DELETE FROM shenas_system.hotkeys")
    for action_id, binding in _DEFAULT_HOTKEYS:
        con.execute(
            "INSERT INTO shenas_system.hotkeys (action_id, binding) VALUES (?, ?)",
            [action_id, binding],
        )


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
