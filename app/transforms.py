"""Transform management: CRUD, seeding defaults, and execution.

Note: The ``sql`` field in transforms is user-supplied SQL that is executed
directly against DuckDB. Any user who can create or edit transforms can run
arbitrary queries. This is by design -- transforms bridge raw pipe data to
canonical schemas and require full SQL expressiveness.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, ClassVar

import duckdb

from app.db import cursor
from shenas_plugins.core.field import Field
from shenas_plugins.core.table import Table

log = logging.getLogger(f"shenas.{__name__}")

_COLS = (
    "id, source_duckdb_schema, source_duckdb_table, target_duckdb_schema,"
    " target_duckdb_table, source_plugin, description, sql, is_default,"
    " enabled, added_at, updated_at, status_changed_at"
)


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


class Transform:
    """Represents a SQL transform stored in shenas_system.transforms."""

    class _Table(Table):
        table_name: ClassVar[str] = "transforms"
        table_display_name: ClassVar[str] = "Transforms"
        table_description: ClassVar[str | None] = (
            "User-supplied SQL transforms bridging source data to canonical metric tables."
        )
        table_pk: ClassVar[tuple[str, ...]] = ("id",)

        id: Annotated[
            int,
            Field(db_type="INTEGER", description="Transform ID", db_default="nextval('shenas_system.transform_seq')"),
        ] = 0
        source_duckdb_schema: Annotated[str, Field(db_type="VARCHAR", description="Source schema")] = ""
        source_duckdb_table: Annotated[str, Field(db_type="VARCHAR", description="Source table")] = ""
        target_duckdb_schema: Annotated[str, Field(db_type="VARCHAR", description="Target schema")] = ""
        target_duckdb_table: Annotated[str, Field(db_type="VARCHAR", description="Target table")] = ""
        source_plugin: Annotated[str, Field(db_type="VARCHAR", description="Source plugin name")] = ""
        description: Annotated[str, Field(db_type="VARCHAR", description="Transform description", db_default="''")] | None = (
            None
        )
        sql: Annotated[str, Field(db_type="TEXT", description="Transform SQL")] = ""
        is_default: (
            Annotated[bool, Field(db_type="BOOLEAN", description="Is a default transform", db_default="FALSE")] | None
        ) = None
        enabled: Annotated[bool, Field(db_type="BOOLEAN", description="Is enabled", db_default="TRUE")] | None = None
        added_at: (
            Annotated[str, Field(db_type="TIMESTAMP", description="When added", db_default="current_timestamp")] | None
        ) = None
        updated_at: Annotated[str, Field(db_type="TIMESTAMP", description="When last updated")] | None = None
        status_changed_at: Annotated[str, Field(db_type="TIMESTAMP", description="When status changed")] | None = None

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        return dict(self._data)

    # -- Queries --

    @staticmethod
    def all(source_plugin: str | None = None) -> list[Transform]:
        with cursor() as cur:
            if source_plugin:
                rows = cur.execute(
                    f"SELECT {_COLS} FROM shenas_system.transforms WHERE source_plugin = ? ORDER BY id",
                    [source_plugin],
                ).fetchall()
            else:
                rows = cur.execute(f"SELECT {_COLS} FROM shenas_system.transforms ORDER BY id").fetchall()
        return [Transform(_row_to_dict(r)) for r in rows]

    @staticmethod
    def find(transform_id: int) -> Transform | None:
        with cursor() as cur:
            row = cur.execute(f"SELECT {_COLS} FROM shenas_system.transforms WHERE id = ?", [transform_id]).fetchone()
        return Transform(_row_to_dict(row)) if row else None

    # -- Mutations --

    @staticmethod
    def create(
        source_duckdb_schema: str,
        source_duckdb_table: str,
        target_duckdb_schema: str,
        target_duckdb_table: str,
        source_plugin: str,
        sql: str,
        description: str = "",
        is_default: bool = False,
    ) -> Transform:
        with cursor() as cur:
            row = cur.execute(
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
            ).fetchone()
        if not row:
            msg = "Failed to create transform"
            raise RuntimeError(msg)
        t = Transform.find(row[0])
        if not t:
            msg = "Failed to create transform"
            raise RuntimeError(msg)
        return t

    def update(self, sql: str) -> Transform | None:
        with cursor() as cur:
            cur.execute(
                "UPDATE shenas_system.transforms SET sql = ?, updated_at = current_timestamp WHERE id = ?",
                [sql, self["id"]],
            )
        return Transform.find(self["id"])

    def delete(self) -> bool:
        if self["is_default"]:
            return False
        with cursor() as cur:
            cur.execute("DELETE FROM shenas_system.transforms WHERE id = ?", [self["id"]])
        return True

    def set_enabled(self, enabled: bool) -> Transform | None:
        with cursor() as cur:
            cur.execute(
                "UPDATE shenas_system.transforms SET enabled = ?,"
                " status_changed_at = current_timestamp,"
                " updated_at = current_timestamp WHERE id = ?",
                [enabled, self["id"]],
            )
        return Transform.find(self["id"])

    def test(self, limit: int = 10) -> list[dict[str, Any]]:
        with cursor() as cur:
            rows = cur.execute(f"SELECT * FROM ({self['sql']}) AS _preview LIMIT {limit}").fetchall()
            cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row, strict=False)) for row in rows]

    # -- Seeding --

    @staticmethod
    def seed_defaults(source_plugin: str, defaults: list[dict[str, str]]) -> None:
        with cursor() as cur:
            existing_defaults = cur.execute(
                "SELECT source_duckdb_table, target_duckdb_table FROM shenas_system.transforms "
                "WHERE source_plugin = ? AND is_default = true",
                [source_plugin],
            ).fetchall()
        existing_keys = {(r[0], r[1]) for r in existing_defaults}
        for d in defaults:
            key = (d["source_duckdb_table"], d["target_duckdb_table"])
            if key in existing_keys:
                with cursor() as cur:
                    cur.execute(
                        "UPDATE shenas_system.transforms SET sql = ?, description = ?,"
                        " updated_at = current_timestamp WHERE source_plugin = ?"
                        " AND source_duckdb_table = ? AND target_duckdb_table = ? AND is_default = true",
                        [
                            d["sql"],
                            d.get("description", ""),
                            source_plugin,
                            d["source_duckdb_table"],
                            d["target_duckdb_table"],
                        ],
                    )
                continue
            Transform.create(
                source_duckdb_schema=d["source_duckdb_schema"],
                source_duckdb_table=d["source_duckdb_table"],
                target_duckdb_schema=d["target_duckdb_schema"],
                target_duckdb_table=d["target_duckdb_table"],
                source_plugin=source_plugin,
                sql=d["sql"],
                description=d.get("description", ""),
                is_default=True,
            )

    # -- Execution --

    @staticmethod
    def run_for_source(con: duckdb.DuckDBPyConnection, source_plugin: str) -> int:
        transforms = Transform.all(source_plugin)
        log.info("Running transforms for %s (%d total)", source_plugin, len(transforms))
        device_id = _get_device_id()
        count = 0
        for t in transforms:
            if not t["enabled"]:
                continue
            count += _execute_transform(con, t, device_id)
        return count

    @staticmethod
    def run_for_target(con: duckdb.DuckDBPyConnection, target_table: str) -> int:
        matching = [t for t in Transform.all() if t["target_duckdb_table"] == target_table and t["enabled"]]
        log.info("Running transforms targeting %s (%d total)", target_table, len(matching))
        device_id = _get_device_id()
        count = 0
        for t in matching:
            count += _execute_transform(con, t, device_id)
        return count


def _get_device_id() -> str:
    try:
        from app.mesh.sync_log import _get_device_id

        return _get_device_id()
    except Exception:
        return "local"


def _ensure_source_device_column(con: duckdb.DuckDBPyConnection, target: str) -> None:
    import contextlib

    with contextlib.suppress(duckdb.Error):
        con.execute(f"ALTER TABLE {target} ADD COLUMN source_device TEXT DEFAULT 'local'")


def _execute_transform(con: duckdb.DuckDBPyConnection, t: Transform, device_id: str) -> int:
    target = f'"{t["target_duckdb_schema"]}"."{t["target_duckdb_table"]}"'
    try:
        con.execute(f"DELETE FROM {target} WHERE source = ?", [t["source_plugin"]])
        with cursor() as cur:
            cur.execute(f"SELECT * FROM ({t['sql']}) _t LIMIT 0")
            cols = [d[0] for d in cur.description]
        col_names = ", ".join(f'"{c}"' for c in cols)
        _ensure_source_device_column(con, target)
        col_names_with_device = col_names + ', "source_device"'
        sql_with_device = f"SELECT *, '{device_id}' as source_device FROM ({t['sql']}) _t"
        con.execute(f"INSERT INTO {target} ({col_names_with_device}) {sql_with_device}")
        return 1
    except Exception:
        log.exception("Transform #%d failed (%s -> %s)", t["id"], t["source_plugin"], target)
        return 0
