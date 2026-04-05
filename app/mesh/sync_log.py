"""Change tracking -- append-only sync log in DuckDB.

Every data mutation (pipe sync, transform, config change) appends an event
to shenas_system.sync_log. The sync engine exchanges events between devices
to replicate changes.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

log = logging.getLogger("shenas.mesh.sync")

_SYNC_LOG_TABLE = """\
CREATE TABLE IF NOT EXISTS shenas_system.sync_log (
    event_id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL,
    table_schema TEXT NOT NULL,
    table_name TEXT NOT NULL,
    row_key TEXT,
    operation TEXT NOT NULL,
    payload TEXT,
    ts BIGINT NOT NULL
)"""

_SYNC_STATE_TABLE = """\
CREATE TABLE IF NOT EXISTS shenas_system.sync_state (
    peer_device_id TEXT PRIMARY KEY,
    last_event_id TEXT,
    last_sync_ts BIGINT
)"""


def ensure_sync_tables() -> None:
    """Create sync tables if they don't exist."""
    from app.db import cursor

    with cursor() as cur:
        cur.execute(_SYNC_LOG_TABLE)
        cur.execute(_SYNC_STATE_TABLE)


def _get_device_id() -> str:
    """Get local device ID from identity table."""
    from app.db import cursor

    with cursor() as cur:
        cur.execute("CREATE TABLE IF NOT EXISTS shenas_system.device_identity (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        row = cur.execute("SELECT value FROM shenas_system.device_identity WHERE key = 'device_id'").fetchone()
        if row:
            return row[0]
        device_id = uuid.uuid4().hex[:16]
        cur.execute(
            "INSERT INTO shenas_system.device_identity (key, value) VALUES ('device_id', ?)",
            [device_id],
        )
        return device_id


def append_event(
    table_schema: str,
    table_name: str,
    operation: str,
    row_key: str | None = None,
    payload: str | None = None,
) -> str:
    """Append a change event to the sync log. Returns the event ID."""
    import time

    from app.db import cursor

    event_id = uuid.uuid4().hex
    device_id = _get_device_id()
    ts = int(time.time() * 1000)

    with cursor() as cur:
        cur.execute(_SYNC_LOG_TABLE)
        cur.execute(
            "INSERT INTO shenas_system.sync_log"
            " (event_id, device_id, table_schema, table_name, row_key, operation, payload, ts)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [event_id, device_id, table_schema, table_name, row_key, operation, payload, ts],
        )

    log.debug("Sync event: %s %s.%s %s", operation, table_schema, table_name, row_key or "")
    return event_id


def get_events_since(last_event_id: str | None = None, limit: int = 1000) -> list[dict[str, Any]]:
    """Get sync log events since a given event ID (exclusive)."""
    from app.db import cursor

    with cursor() as cur:
        cur.execute(_SYNC_LOG_TABLE)
        if last_event_id:
            ts_row = cur.execute(
                "SELECT ts FROM shenas_system.sync_log WHERE event_id = ?",
                [last_event_id],
            ).fetchone()
            if ts_row:
                rows = cur.execute(
                    "SELECT event_id, device_id, table_schema, table_name,"
                    " row_key, operation, payload, ts"
                    " FROM shenas_system.sync_log WHERE ts > ? ORDER BY ts LIMIT ?",
                    [ts_row[0], limit],
                ).fetchall()
            else:
                rows = cur.execute(
                    "SELECT event_id, device_id, table_schema, table_name,"
                    " row_key, operation, payload, ts"
                    " FROM shenas_system.sync_log ORDER BY ts LIMIT ?",
                    [limit],
                ).fetchall()
        else:
            rows = cur.execute(
                "SELECT event_id, device_id, table_schema, table_name,"
                " row_key, operation, payload, ts"
                " FROM shenas_system.sync_log ORDER BY ts LIMIT ?",
                [limit],
            ).fetchall()
        cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r, strict=False)) for r in rows]


def get_sync_cursor(peer_device_id: str) -> str | None:
    """Get the last synced event ID for a peer."""
    from app.db import cursor

    with cursor() as cur:
        cur.execute(_SYNC_STATE_TABLE)
        row = cur.execute(
            "SELECT last_event_id FROM shenas_system.sync_state WHERE peer_device_id = ?",
            [peer_device_id],
        ).fetchone()
    return row[0] if row else None


def set_sync_cursor(peer_device_id: str, last_event_id: str) -> None:
    """Update the sync cursor for a peer."""
    import time

    from app.db import cursor

    with cursor() as cur:
        cur.execute(_SYNC_STATE_TABLE)
        cur.execute(
            "INSERT INTO shenas_system.sync_state (peer_device_id, last_event_id, last_sync_ts)"
            " VALUES (?, ?, ?) ON CONFLICT (peer_device_id)"
            " DO UPDATE SET last_event_id = ?, last_sync_ts = ?",
            [peer_device_id, last_event_id, int(time.time() * 1000), last_event_id, int(time.time() * 1000)],
        )
