"""Transform: SQL transforms bridging raw source tables to canonical metrics.

Two classes:

- :class:`TransformInstance` -- the row in ``shenas_system.transforms``.
  One row per SQL transform, keyed by auto-increment ``id``. Carries the
  SQL, source/target mapping, enabled state, and lifecycle timestamps.
  Row-level CRUD comes from :class:`Table`.

- :class:`Transform` -- the behavior class (a :class:`Plugin` kind).
  Classmethods/staticmethods that operate across ``TransformInstance``
  rows: creating, seeding defaults from a source's ``transforms.json``,
  and executing transforms after a sync.

Note: The ``sql`` field in transforms is user-supplied SQL that is executed
directly against DuckDB. Any user who can create or edit transforms can run
arbitrary queries. This is by design -- transforms bridge raw pipe data to
canonical schemas and require full SQL expressiveness.
"""

from __future__ import annotations

import dataclasses
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Any

import duckdb

from app.db import cursor
from shenas_plugins.core.plugin import Plugin
from shenas_plugins.core.table import Field, Table

log = logging.getLogger(f"shenas.{__name__}")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


# ----------------------------------------------------------------------
# TransformInstance -- the row
# ----------------------------------------------------------------------


@dataclass
class TransformInstance(Table):
    """A single SQL transform row in ``shenas_system.transforms``."""

    class _Meta:
        name = "transforms"
        display_name = "Transforms"
        description = "User-supplied SQL transforms bridging source data to canonical metric tables."
        schema = "shenas_system"
        pk = ("id",)

    id: Annotated[
        int,
        Field(db_type="INTEGER", description="Transform ID", db_default="nextval('shenas_system.transform_seq')"),
    ] = 0
    source_duckdb_schema: Annotated[str, Field(db_type="VARCHAR", description="Source schema")] = ""
    source_duckdb_table: Annotated[str, Field(db_type="VARCHAR", description="Source table")] = ""
    target_duckdb_schema: Annotated[str, Field(db_type="VARCHAR", description="Target schema")] = ""
    target_duckdb_table: Annotated[str, Field(db_type="VARCHAR", description="Target table")] = ""
    source_plugin: Annotated[str, Field(db_type="VARCHAR", description="Source plugin name")] = ""
    description: Annotated[str, Field(db_type="VARCHAR", description="Transform description", db_default="''")] | None = None
    sql: Annotated[str, Field(db_type="TEXT", description="Transform SQL")] = ""
    is_default: Annotated[bool, Field(db_type="BOOLEAN", description="Is a default transform", db_default="FALSE")] | None = (
        None
    )
    enabled: Annotated[bool, Field(db_type="BOOLEAN", description="Is enabled", db_default="TRUE")] | None = None
    added_at: Annotated[str, Field(db_type="TIMESTAMP", description="When added", db_default="current_timestamp")] | None = (
        None
    )
    updated_at: Annotated[str, Field(db_type="TIMESTAMP", description="When last updated")] | None = None
    status_changed_at: Annotated[str, Field(db_type="TIMESTAMP", description="When status changed")] | None = None

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def for_plugin(cls, source_plugin: str) -> list[TransformInstance]:
        """All transforms registered against one source plugin, ordered by id."""
        return cls.all(where="source_plugin = ?", params=[source_plugin], order_by="id")

    def update(self, sql: str) -> TransformInstance:
        """Update the SQL and bump ``updated_at``."""
        self.sql = sql
        self.updated_at = _now_iso()
        return self.save()

    def set_enabled(self, enabled: bool) -> TransformInstance:
        """Toggle ``enabled`` and bump timestamps."""
        now = _now_iso()
        self.enabled = enabled
        self.status_changed_at = now
        self.updated_at = now
        return self.save()

    def delete(self) -> None:  # type: ignore[override]
        """Delete this transform. Default transforms are protected (no-op)."""
        if self.is_default:
            return
        super().delete()

    def test(self, limit: int = 10) -> list[dict[str, Any]]:
        """Run the transform's SQL with a LIMIT, return rows as dicts."""
        with cursor() as cur:
            rows = cur.execute(f"SELECT * FROM ({self.sql}) AS _preview LIMIT {limit}").fetchall()
            cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row, strict=False)) for row in rows]


# ----------------------------------------------------------------------
# Transform -- the behavior (Plugin kind)
# ----------------------------------------------------------------------


class Transform(Plugin):
    """The transform subsystem as a Plugin kind.

    Provides classmethods that operate across :class:`TransformInstance`
    rows: creating new transforms, seeding defaults from a source's
    ``transforms.json``, and executing enabled transforms after a sync.
    """

    name = "transform"
    display_name = "Transforms"
    description = "SQL transforms bridging raw source tables to canonical metrics."
    internal = True

    @property
    def _kind(self) -> str:
        return "transform"

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
    ) -> TransformInstance:
        t = TransformInstance(
            source_duckdb_schema=source_duckdb_schema,
            source_duckdb_table=source_duckdb_table,
            target_duckdb_schema=target_duckdb_schema,
            target_duckdb_table=target_duckdb_table,
            source_plugin=source_plugin,
            sql=sql,
            description=description,
            is_default=is_default,
        )
        return t.insert()

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

    @staticmethod
    def run_for_source(con: duckdb.DuckDBPyConnection, source_plugin: str) -> int:
        transforms = TransformInstance.for_plugin(source_plugin)
        log.info("Running transforms for %s (%d total)", source_plugin, len(transforms))
        device_id = _get_device_id()
        count = 0
        for t in transforms:
            if not t.enabled:
                continue
            count += _execute_transform(con, t, device_id)
        return count

    @staticmethod
    def run_for_target(con: duckdb.DuckDBPyConnection, target_table: str) -> int:
        matching = [t for t in TransformInstance.all(order_by="id") if t.target_duckdb_table == target_table and t.enabled]
        log.info("Running transforms targeting %s (%d total)", target_table, len(matching))
        device_id = _get_device_id()
        count = 0
        for t in matching:
            count += _execute_transform(con, t, device_id)
        return count


# ----------------------------------------------------------------------
# Module-level helpers
# ----------------------------------------------------------------------


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


def _execute_transform(con: duckdb.DuckDBPyConnection, t: TransformInstance, device_id: str) -> int:
    target = f'"{t.target_duckdb_schema}"."{t.target_duckdb_table}"'
    try:
        con.execute(f"DELETE FROM {target} WHERE source = ?", [t.source_plugin])
        with cursor() as cur:
            cur.execute(f"SELECT * FROM ({t.sql}) _t LIMIT 0")
            cols = [d[0] for d in cur.description]
        col_names = ", ".join(f'"{c}"' for c in cols)
        _ensure_source_device_column(con, target)
        col_names_with_device = col_names + ', "source_device"'
        sql_with_device = f"SELECT *, '{device_id}' as source_device FROM ({t.sql}) _t"
        con.execute(f"INSERT INTO {target} ({col_names_with_device}) {sql_with_device}")
        return 1
    except Exception:
        log.exception("Transform #%d failed (%s -> %s)", t.id, t.source_plugin, target)
        return 0
