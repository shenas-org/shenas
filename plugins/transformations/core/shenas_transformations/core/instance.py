"""TransformInstance: configured transform instances stored in DuckDB.

Each row is one configured transform -- a binding between a source table,
a target table, a transformation type, and type-specific params. The
``transform_type`` column selects which Transform plugin executes it.
"""

from __future__ import annotations

import dataclasses
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Any

from shenas_plugins.core.table import Field, Table

if TYPE_CHECKING:
    import duckdb

log = logging.getLogger(f"shenas.{__name__}")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class TransformInstance(Table):
    """A configured transform instance in ``shenas_system.transform_instances``."""

    class _Meta:
        name = "transform_instances"
        display_name = "Transform Instances"
        description = "Configured transform instances binding source tables to target tables."
        schema = "shenas_system"
        pk = ("id",)

    id: Annotated[
        int,
        Field(
            db_type="INTEGER",
            description="Instance ID",
            db_default="nextval('shenas_system.transform_instance_seq')",
        ),
    ] = 0
    transform_type: Annotated[str, Field(db_type="VARCHAR", description="Transform plugin name")] = "sql"
    source_duckdb_schema: Annotated[str, Field(db_type="VARCHAR", description="Source schema")] = ""
    source_duckdb_table: Annotated[str, Field(db_type="VARCHAR", description="Source table")] = ""
    target_duckdb_schema: Annotated[str, Field(db_type="VARCHAR", description="Target schema")] = ""
    target_duckdb_table: Annotated[str, Field(db_type="VARCHAR", description="Target table")] = ""
    source_plugin: Annotated[str, Field(db_type="VARCHAR", description="Source plugin name")] = ""
    params: Annotated[str, Field(db_type="TEXT", description="Type-specific params as JSON", db_default="'{}'")] = "{}"
    description: Annotated[str, Field(db_type="VARCHAR", description="Transform description", db_default="''")] | None = None
    is_default: Annotated[bool, Field(db_type="BOOLEAN", description="Is a default transform", db_default="FALSE")] | None = (
        None
    )
    enabled: Annotated[bool, Field(db_type="BOOLEAN", description="Is enabled", db_default="TRUE")] | None = None
    added_at: Annotated[str, Field(db_type="TIMESTAMP", description="When added", db_default="current_timestamp")] | None = (
        None
    )
    updated_at: Annotated[str, Field(db_type="TIMESTAMP", description="When last updated")] | None = None
    status_changed_at: Annotated[str, Field(db_type="TIMESTAMP", description="When status changed")] | None = None

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    def get_params(self) -> dict[str, Any]:
        """Parse the params JSON blob."""
        try:
            return json.loads(self.params) if self.params else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @classmethod
    def for_plugin(cls, source_plugin: str) -> list[TransformInstance]:
        return cls.all(where="source_plugin = ?", params=[source_plugin], order_by="id")

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        *,
        transform_type: str,
        source_duckdb_schema: str,
        source_duckdb_table: str,
        target_duckdb_schema: str,
        target_duckdb_table: str,
        source_plugin: str,
        params: str = "{}",
        description: str = "",
        is_default: bool = False,
    ) -> TransformInstance:
        t = cls(
            transform_type=transform_type,
            source_duckdb_schema=source_duckdb_schema,
            source_duckdb_table=source_duckdb_table,
            target_duckdb_schema=target_duckdb_schema,
            target_duckdb_table=target_duckdb_table,
            source_plugin=source_plugin,
            params=params,
            description=description,
            is_default=is_default,
        )
        return t.insert()

    def update_params(self, params: str) -> TransformInstance:
        self.params = params
        self.updated_at = _now_iso()
        return self.save()

    def set_enabled(self, enabled: bool) -> TransformInstance:
        now = _now_iso()
        self.enabled = enabled
        self.status_changed_at = now
        self.updated_at = now
        return self.save()

    def delete(self) -> None:  # type: ignore[override]
        if self.is_default:
            return
        super().delete()

    def test(self, limit: int = 10) -> list[dict[str, Any]]:
        """Preview output. Only works for SQL transforms."""
        p = self.get_params()
        sql = p.get("sql", "")
        if not sql:
            return []
        from app.db import cursor

        with cursor() as cur:
            rows = cur.execute(f"SELECT * FROM ({sql}) AS _preview LIMIT {limit}").fetchall()
            cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row, strict=False)) for row in rows]

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    @classmethod
    def seed_defaults(
        cls,
        source_plugin: str,
        transform_type: str,
        defaults: list[dict[str, str]],
    ) -> None:
        from app.db import cursor

        with cursor() as cur:
            existing = cur.execute(
                "SELECT source_duckdb_table, target_duckdb_table "
                "FROM shenas_system.transform_instances "
                "WHERE source_plugin = ? AND transform_type = ? AND is_default = true",
                [source_plugin, transform_type],
            ).fetchall()
        existing_keys = {(r[0], r[1]) for r in existing}

        for d in defaults:
            key = (d["source_duckdb_table"], d["target_duckdb_table"])
            params_json = d.get("params", "{}")
            if key in existing_keys:
                with cursor() as cur:
                    cur.execute(
                        "UPDATE shenas_system.transform_instances "
                        "SET params = ?, description = ?, updated_at = current_timestamp "
                        "WHERE source_plugin = ? AND transform_type = ? "
                        "AND source_duckdb_table = ? AND target_duckdb_table = ? "
                        "AND is_default = true",
                        [
                            params_json,
                            d.get("description", ""),
                            source_plugin,
                            transform_type,
                            d["source_duckdb_table"],
                            d["target_duckdb_table"],
                        ],
                    )
                continue
            cls.create(
                transform_type=transform_type,
                source_duckdb_schema=d["source_duckdb_schema"],
                source_duckdb_table=d["source_duckdb_table"],
                target_duckdb_schema=d["target_duckdb_schema"],
                target_duckdb_table=d["target_duckdb_table"],
                source_plugin=source_plugin,
                params=params_json,
                description=d.get("description", ""),
                is_default=True,
            )

    # ------------------------------------------------------------------
    # Execution (dispatches to Transform plugins)
    # ------------------------------------------------------------------

    @staticmethod
    def run_for_source(con: duckdb.DuckDBPyConnection, source_plugin: str) -> int:
        instances = TransformInstance.for_plugin(source_plugin)
        log.info("Running transforms for %s (%d total)", source_plugin, len(instances))
        device_id = _get_device_id()
        plugin_cache: dict[str, Any] = {}
        count = 0
        for inst in instances:
            if not inst.enabled:
                continue
            plugin = _get_transform_plugin(inst.transform_type, plugin_cache)
            if plugin is None:
                log.warning(
                    "No transformation plugin for type=%s, skipping #%d",
                    inst.transform_type,
                    inst.id,
                )
                continue
            count += plugin.execute(con, inst, device_id=device_id)
        return count

    @staticmethod
    def run_for_target(con: duckdb.DuckDBPyConnection, target_table: str) -> int:
        matching = [t for t in TransformInstance.all(order_by="id") if t.target_duckdb_table == target_table and t.enabled]
        log.info("Running transforms targeting %s (%d total)", target_table, len(matching))
        device_id = _get_device_id()
        plugin_cache: dict[str, Any] = {}
        count = 0
        for inst in matching:
            plugin = _get_transform_plugin(inst.transform_type, plugin_cache)
            if plugin is None:
                log.warning(
                    "No transformation plugin for type=%s, skipping #%d",
                    inst.transform_type,
                    inst.id,
                )
                continue
            count += plugin.execute(con, inst, device_id=device_id)
        return count


def _get_device_id() -> str:
    try:
        from app.mesh.sync_log import _get_device_id

        return _get_device_id()
    except Exception:
        return "local"


def _get_transform_plugin(transform_type: str, cache: dict[str, Any]) -> Any:
    if transform_type not in cache:
        from app.api.sources import _load_plugin

        cls = _load_plugin("transformation", transform_type)
        cache[transform_type] = cls() if cls else None
    return cache[transform_type]
