"""Transform: configured transform instances stored in DuckDB.

Each row is one configured transform -- a binding between a source table,
a target table, a transformation type, and type-specific params. The
``transform_type`` column selects which Transformer plugin executes it.
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Any

from app.catalog import DataResourceRef
from app.plugin import Plugin
from app.schema import TRANSFORMS
from app.table import Field, Table

log = Plugin.get_logger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class Transform(Table):
    """A configured transform instance in ``transforms.instances``."""

    class _Meta:
        name = "instances"
        display_name = "Transforms"
        description = "Configured transform instances binding source tables to target tables."
        schema = TRANSFORMS
        pk = ("id",)
        sequences = ("transforms.transform_instance_seq",)

    id: Annotated[
        int,
        Field(
            db_type="INTEGER",
            description="Instance ID",
            db_default="nextval('transforms.transform_instance_seq')",
        ),
    ] = 0
    transform_type: Annotated[str, Field(db_type="VARCHAR", description="Transformer plugin name")] = "sql"
    source_data_resource_id: Annotated[str, Field(db_type="VARCHAR", description="Source data resource (schema.table)")] = ""
    target_data_resource_id: Annotated[str, Field(db_type="VARCHAR", description="Target data resource (schema.table)")] = ""
    source_plugin: Annotated[str, Field(db_type="VARCHAR", description="Source plugin name")] = ""
    params: Annotated[str, Field(db_type="TEXT", description="Type-specific params as JSON", db_default="'{}'")] = "{}"
    description: Annotated[str, Field(db_type="VARCHAR", description="Transform description", db_default="''")] | None = None
    is_default: Annotated[bool, Field(db_type="BOOLEAN", description="Is a default transform", db_default="FALSE")] | None = (
        None
    )
    enabled: Annotated[bool, Field(db_type="BOOLEAN", description="Is enabled", db_default="TRUE")] | None = None
    is_suggested: (
        Annotated[bool, Field(db_type="BOOLEAN", description="LLM-suggested, not yet accepted", db_default="FALSE")] | None
    ) = None
    added_at: Annotated[str, Field(db_type="TIMESTAMP", description="When added", db_default="current_timestamp")] | None = (
        None
    )
    updated_at: Annotated[str, Field(db_type="TIMESTAMP", description="When last updated")] | None = None
    status_changed_at: Annotated[str, Field(db_type="TIMESTAMP", description="When status changed")] | None = None

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @property
    def source_ref(self) -> DataResourceRef:
        return DataResourceRef.from_id(self.source_data_resource_id)

    @property
    def target_ref(self) -> DataResourceRef:
        return DataResourceRef.from_id(self.target_data_resource_id)

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
    def for_plugin(cls, source_plugin: str) -> list[Transform]:
        return cls.all(where="source_plugin = ?", params=[source_plugin], order_by="id")

    @classmethod
    def suggested(cls, source_plugin: str | None = None) -> list[Transform]:
        """List suggested (not yet accepted) transform instances."""
        if source_plugin:
            return cls.all(
                where="is_suggested = TRUE AND source_plugin = ?",
                params=[source_plugin],
                order_by="id",
            )
        return cls.all(where="is_suggested = TRUE", order_by="id")

    # ------------------------------------------------------------------
    # Suggestion lifecycle
    # ------------------------------------------------------------------

    @classmethod
    def create_suggested(
        cls,
        *,
        transform_type: str = "sql",
        source_data_resource_id: str,
        target_data_resource_id: str,
        source_plugin: str,
        params: str = "{}",
        description: str = "",
    ) -> Transform:
        """Create a suggested transform instance (disabled until accepted)."""
        transform = cls(
            transform_type=transform_type,
            source_data_resource_id=source_data_resource_id,
            target_data_resource_id=target_data_resource_id,
            source_plugin=source_plugin,
            params=params,
            description=description,
            is_suggested=True,
            enabled=False,
        )
        return transform.insert()

    def accept_suggestion(self) -> Transform:
        """Accept: flip is_suggested, enable the transform."""
        now = _now_iso()
        self.is_suggested = False
        self.enabled = True
        self.updated_at = now
        return self.save()

    def dismiss_suggestion(self) -> None:
        """Dismiss: delete the suggested transform."""
        super().delete()

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        *,
        transform_type: str,
        source_data_resource_id: str,
        target_data_resource_id: str,
        source_plugin: str,
        params: str = "{}",
        description: str = "",
        is_default: bool = False,
    ) -> Transform:
        transform = cls(
            transform_type=transform_type,
            source_data_resource_id=source_data_resource_id,
            target_data_resource_id=target_data_resource_id,
            source_plugin=source_plugin,
            params=params,
            description=description,
            is_default=is_default,
        )
        return transform.insert()

    def update_params(self, params: str) -> Transform:
        self.params = params
        self.updated_at = _now_iso()
        return self.save()

    def set_enabled(self, enabled: bool) -> Transform:
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
        from app.database import cursor

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
        existing = cls.all(
            where="source_plugin = ? AND transform_type = ? AND is_default = true",
            params=[source_plugin, transform_type],
        )
        existing_by_key = {
            (transform.source_data_resource_id, transform.target_data_resource_id): transform for transform in existing
        }

        for d in defaults:
            src_id = f"{d['source_duckdb_schema']}.{d['source_duckdb_table']}"
            tgt_id = f"{d['target_duckdb_schema']}.{d['target_duckdb_table']}"
            key = (src_id, tgt_id)
            params_json = d.get("params", "{}")
            if key in existing_by_key:
                transform = existing_by_key[key]
                transform.params = params_json
                transform.description = d.get("description", "")
                transform.save()
                continue
            cls.create(
                transform_type=transform_type,
                source_data_resource_id=src_id,
                target_data_resource_id=tgt_id,
                source_plugin=source_plugin,
                params=params_json,
                description=d.get("description", ""),
                is_default=True,
            )

    # ------------------------------------------------------------------
    # Execution (dispatches to Transformer plugins)
    # ------------------------------------------------------------------

    @staticmethod
    def run_for_source(source_plugin: str) -> int:
        transforms = Transform.for_plugin(source_plugin)
        log.info("Running transforms for %s (%d total)", source_plugin, len(transforms))
        device_id = _get_device_id()
        plugin_cache: dict[str, Any] = {}
        count = 0
        for transform in transforms:
            if not transform.enabled:
                continue
            if not transform.source_data_resource_id or not transform.target_data_resource_id:
                log.warning(
                    "Transform #%d missing source/target resource id, skipping (source=%r target=%r)",
                    transform.id,
                    transform.source_data_resource_id,
                    transform.target_data_resource_id,
                )
                continue
            plugin = _get_transform_plugin(transform.transform_type, plugin_cache)
            if plugin is None:
                log.warning(
                    "No transformer plugin for type=%s, skipping #%d",
                    transform.transform_type,
                    transform.id,
                )
                continue
            result = plugin.execute(transform, device_id=device_id)
            if result:
                try:
                    from app.data_catalog import catalog

                    catalog().mark_refreshed(transform.target_ref.schema, transform.target_ref.table)
                except Exception:
                    pass
                try:
                    from app.pubsub import pubsub

                    pubsub.publish_sync(
                        "table_data_changed",
                        {"schema": transform.target_ref.schema, "table": transform.target_ref.table},
                    )
                except Exception:
                    pass
            count += result
        return count

    @staticmethod
    def run_for_target(target_table: str) -> int:
        matching = [
            transform
            for transform in Transform.all(order_by="id")
            if transform.enabled and transform.target_data_resource_id and transform.target_ref.table == target_table
        ]
        log.info("Running transforms targeting %s (%d total)", target_table, len(matching))
        device_id = _get_device_id()
        plugin_cache: dict[str, Any] = {}
        count = 0
        for transform in matching:
            plugin = _get_transform_plugin(transform.transform_type, plugin_cache)
            if plugin is None:
                log.warning(
                    "No transformer plugin for type=%s, skipping #%d",
                    transform.transform_type,
                    transform.id,
                )
                continue
            result = plugin.execute(transform, device_id=device_id)
            if result:
                try:
                    from app.data_catalog import catalog

                    catalog().mark_refreshed(transform.target_ref.schema, transform.target_ref.table)
                except Exception:
                    pass
                try:
                    from app.pubsub import pubsub

                    pubsub.publish_sync(
                        "table_data_changed",
                        {"schema": transform.target_ref.schema, "table": transform.target_ref.table},
                    )
                except Exception:
                    pass
            count += result
        return count


def _get_device_id() -> str:
    try:
        from app.mesh.sync_log import _get_device_id

        return _get_device_id()
    except Exception:
        return "local"


def _get_transform_plugin(transform_type: str, cache: dict[str, Any]) -> Any:
    if transform_type not in cache:
        from shenas_transformers.core import Transformer

        cls = Transformer.load_by_name(transform_type)
        cache[transform_type] = cls() if cls else None
    return cache[transform_type]
