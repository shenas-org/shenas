"""Transform management: CRUD, seeding defaults, and execution.

Note: The ``sql`` field in transforms is user-supplied SQL that is executed
directly against DuckDB. Any user who can create or edit transforms can run
arbitrary queries. This is by design -- transforms bridge raw pipe data to
canonical schemas and require full SQL expressiveness.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.db import connect

if TYPE_CHECKING:
    import duckdb

log = logging.getLogger(f"shenas.{__name__}")

_COLS = (
    "id, source_duckdb_schema, source_duckdb_table, target_duckdb_schema,"
    " target_duckdb_table, source_plugin, description, sql, is_default,"
    " enabled, added_at, updated_at, status_changed_at"
)


def _cursor() -> duckdb.DuckDBPyConnection:
    """Return a fresh cursor on the shared connection with USE db set."""
    cur = connect().cursor()
    cur.execute("USE db")
    return cur


def _row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": row[0],
        "source_duckdb_schema": row[1],
        "source_duckdb_table": row[2],
        "target_duckdb_schema": row[3],
        "target_duckdb_table": row[4],
        "source_plugin": row[5],
        "description": row[6] or "",
        "sql": row[7],
        "is_default": row[8],
        "enabled": row[9],
        "added_at": str(row[10]) if row[10] else None,
        "updated_at": str(row[11]) if row[11] else None,
        "status_changed_at": str(row[12]) if row[12] else None,
    }


def list_transforms(source_plugin: str | None = None) -> list[dict[str, Any]]:
    """List transforms, optionally filtered by source plugin."""
    cur = _cursor()
    if source_plugin:
        rows = cur.execute(
            f"SELECT {_COLS} FROM shenas_system.transforms WHERE source_plugin = ? ORDER BY id",
            [source_plugin],
        ).fetchall()
    else:
        rows = cur.execute(f"SELECT {_COLS} FROM shenas_system.transforms ORDER BY id").fetchall()
    cur.close()
    return [_row_to_dict(r) for r in rows]


def get_transform(transform_id: int) -> dict[str, Any] | None:
    """Get a single transform by ID."""
    cur = _cursor()
    row = cur.execute(f"SELECT {_COLS} FROM shenas_system.transforms WHERE id = ?", [transform_id]).fetchone()
    cur.close()
    return _row_to_dict(row) if row else None


def create_transform(
    source_duckdb_schema: str,
    source_duckdb_table: str,
    target_duckdb_schema: str,
    target_duckdb_table: str,
    source_plugin: str,
    sql: str,
    description: str = "",
    is_default: bool = False,
) -> dict[str, Any]:
    """Create a new transform and return it."""
    cur = _cursor()
    cur.execute(
        "INSERT INTO shenas_system.transforms "
        "(source_duckdb_schema, source_duckdb_table, target_duckdb_schema,"
        " target_duckdb_table, source_plugin, description, sql, is_default) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING id",
        [
            source_duckdb_schema,
            source_duckdb_table,
            target_duckdb_schema,
            target_duckdb_table,
            source_plugin,
            description,
            sql,
            is_default,
        ],
    )
    result = cur.fetchone()
    if not result:
        msg = "Failed to create transform"
        raise RuntimeError(msg)
    new_id = result[0]
    cur.close()
    row = get_transform(new_id)
    if not row:
        msg = "Failed to create transform"
        raise RuntimeError(msg)
    return row


def update_transform(transform_id: int, sql: str) -> dict[str, Any] | None:
    """Update a transform's SQL. Returns None if not found."""
    cur = _cursor()
    cur.execute(
        "UPDATE shenas_system.transforms SET sql = ?, updated_at = current_timestamp WHERE id = ?",
        [sql, transform_id],
    )
    cur.close()
    return get_transform(transform_id)


def delete_transform(transform_id: int) -> bool:
    """Delete a non-default transform. Returns False if not found or is_default."""
    t = get_transform(transform_id)
    if not t or t["is_default"]:
        return False
    cur = _cursor()
    cur.execute("DELETE FROM shenas_system.transforms WHERE id = ?", [transform_id])
    cur.close()
    return True


def set_transform_enabled(transform_id: int, enabled: bool) -> dict[str, Any] | None:
    """Enable or disable a transform."""
    t = get_transform(transform_id)
    if not t:
        return None
    cur = _cursor()
    cur.execute(
        "UPDATE shenas_system.transforms SET enabled = ?,"
        " status_changed_at = current_timestamp,"
        " updated_at = current_timestamp WHERE id = ?",
        [enabled, transform_id],
    )
    cur.close()
    return get_transform(transform_id)


def seed_defaults(source_plugin: str, defaults: list[dict[str, str]]) -> None:
    """Seed default transforms for a source plugin.

    Only inserts defaults that don't already exist (by is_default=true).
    Existing user-created transforms do not block seeding.
    """
    cur = _cursor()
    existing_defaults = cur.execute(
        "SELECT source_duckdb_table, target_duckdb_table FROM shenas_system.transforms "
        "WHERE source_plugin = ? AND is_default = true",
        [source_plugin],
    ).fetchall()
    cur.close()
    existing_keys = {(r[0], r[1]) for r in existing_defaults}
    for d in defaults:
        key = (d["source_duckdb_table"], d["target_duckdb_table"])
        if key in existing_keys:
            # Update SQL and description if changed
            cur2 = _cursor()
            cur2.execute(
                "UPDATE shenas_system.transforms SET sql = ?, description = ?, updated_at = current_timestamp "
                "WHERE source_plugin = ? AND source_duckdb_table = ? AND target_duckdb_table = ? AND is_default = true",
                [d["sql"], d.get("description", ""), source_plugin, d["source_duckdb_table"], d["target_duckdb_table"]],
            )
            cur2.close()
            continue
        create_transform(
            source_duckdb_schema=d["source_duckdb_schema"],
            source_duckdb_table=d["source_duckdb_table"],
            target_duckdb_schema=d["target_duckdb_schema"],
            target_duckdb_table=d["target_duckdb_table"],
            source_plugin=source_plugin,
            sql=d["sql"],
            description=d.get("description", ""),
            is_default=True,
        )


def run_transforms(con: duckdb.DuckDBPyConnection, source_plugin: str) -> int:
    """Run all enabled transforms for a source plugin.

    Uses the caller's connection for DELETE/INSERT (the pipe's sync connection)
    and a separate cursor for reading transform definitions from the system table.
    """
    transforms = list_transforms(source_plugin)
    log.info("Running transforms for %s (%d total)", source_plugin, len(transforms))
    count = 0
    for t in transforms:
        if not t["enabled"]:
            continue
        target = f'"{t["target_duckdb_schema"]}"."{t["target_duckdb_table"]}"'
        try:
            con.execute(f"DELETE FROM {target} WHERE source = ?", [t["source_plugin"]])
            con.execute(f"INSERT INTO {target} {t['sql']}")
            count += 1
        except Exception:
            log.exception("Transform #%d failed (%s -> %s)", t["id"], t["source_plugin"], target)
    return count


def test_transform(transform_id: int, limit: int = 10) -> list[dict[str, Any]]:  # noqa: PT028
    """Dry-run a transform's SQL and return preview rows."""
    t = get_transform(transform_id)
    if not t:
        return []
    cur = _cursor()
    rows = cur.execute(f"SELECT * FROM ({t['sql']}) AS _preview LIMIT {limit}").fetchall()
    cols = [desc[0] for desc in cur.description]
    cur.close()
    return [dict(zip(cols, row, strict=False)) for row in rows]
