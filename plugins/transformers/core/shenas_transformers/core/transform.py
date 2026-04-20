"""Transform: configured transform pipelines stored in DuckDB.

A Transform is a pipeline of one or more TransformSteps. Each step
binds a Transformer plugin type to type-specific params. Steps execute
in ordinal order, with intermediate results passing through temp tables.

Legacy single-step transforms (with ``transform_type`` and ``params``
directly on the Transform row) are auto-migrated to a single
TransformStep on first access.
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


# ---------------------------------------------------------------------------
# TransformStep -- one step in a transform pipeline
# ---------------------------------------------------------------------------


@dataclass
class TransformStep(Table):
    """A single step within a transform pipeline."""

    class _Meta:
        name = "steps"
        display_name = "Transform Steps"
        description = "Individual steps within transform pipelines."
        schema = TRANSFORMS
        pk = ("id",)
        sequences = ("transforms.transform_step_seq",)

    id: Annotated[
        int,
        Field(
            db_type="INTEGER",
            description="Step ID",
            db_default="nextval('transforms.transform_step_seq')",
        ),
    ] = 0
    transform_id: Annotated[int, Field(db_type="INTEGER", description="Parent transform ID")] = 0
    ordinal: Annotated[int, Field(db_type="INTEGER", description="Execution order (0-based)")] = 0
    transformer: Annotated[str, Field(db_type="VARCHAR", description="Transformer plugin name")] = "sql"
    params: Annotated[str, Field(db_type="TEXT", description="Type-specific params as JSON", db_default="'{}'")] = "{}"
    description: Annotated[str, Field(db_type="VARCHAR", description="Step description", db_default="''")] | None = None

    def get_params(self) -> dict[str, Any]:
        """Parse the params JSON blob."""
        try:
            return json.loads(self.params) if self.params else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    @classmethod
    def for_transform(cls, transform_id: int) -> list[TransformStep]:
        cls.ensure()
        return cls.all(where="transform_id = ?", params=[transform_id], order_by="ordinal")

    @classmethod
    def create(
        cls,
        *,
        transform_id: int,
        ordinal: int,
        transformer: str,
        params: str = "{}",
        description: str = "",
    ) -> TransformStep:
        step = cls(
            transform_id=transform_id,
            ordinal=ordinal,
            transformer=transformer,
            params=params,
            description=description,
        )
        return step.insert()

    @classmethod
    def delete_for_transform(cls, transform_id: int) -> None:
        cls.ensure()
        from app.database import cursor

        with cursor() as con:
            con.execute(
                f'DELETE FROM "{cls._Meta.schema.name}"."{cls._Meta.name}" WHERE transform_id = ?',
                [transform_id],
            )


# ---------------------------------------------------------------------------
# Transform -- the pipeline container
# ---------------------------------------------------------------------------


@dataclass
class Transform(Table):
    """A configured transform pipeline in ``transforms.instances``."""

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
    # Steps
    # ------------------------------------------------------------------

    @property
    def steps(self) -> list[TransformStep]:
        """Return ordered steps for this pipeline."""
        return TransformStep.for_transform(self.id)

    def set_steps(self, steps: list[dict[str, Any]]) -> None:
        """Replace all steps with the given list of step dicts.

        Each dict: ``{transformer: str, params: str, description?: str}``
        """
        TransformStep.delete_for_transform(self.id)
        for ordinal, step_data in enumerate(steps):
            TransformStep.create(
                transform_id=self.id,
                ordinal=ordinal,
                transformer=step_data["transformer"],
                params=step_data.get("params", "{}"),
                description=step_data.get("description", ""),
            )
        self.updated_at = _now_iso()
        self.save()

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
        steps: list[dict[str, Any]] | None = None,
    ) -> Transform:
        TransformStep.ensure()
        transform = cls(
            transform_type=transform_type,
            source_data_resource_id=source_data_resource_id,
            target_data_resource_id=target_data_resource_id,
            source_plugin=source_plugin,
            params=params,
            description=description,
            is_default=is_default,
        )
        transform = transform.insert()
        # Create steps if provided, otherwise auto-create from legacy fields
        if steps:
            for ordinal, step_data in enumerate(steps):
                TransformStep.create(
                    transform_id=transform.id,
                    ordinal=ordinal,
                    transformer=step_data["transformer"],
                    params=step_data.get("params", "{}"),
                    description=step_data.get("description", ""),
                )
        else:
            TransformStep.create(
                transform_id=transform.id,
                ordinal=0,
                transformer=transform_type,
                params=params,
                description=description or "",
            )
        return transform

    def update_params(self, params: str) -> Transform:
        self.params = params
        self.updated_at = _now_iso()
        steps = self.steps
        if steps:
            steps[0].params = params
            steps[0].save()
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
        TransformStep.delete_for_transform(self.id)
        super().delete()

    def test(self, limit: int = 10) -> list[dict[str, Any]]:
        """Preview output. Works for SQL transforms (raw or structured)."""
        params = self.get_params()

        # Structured mode: build SQL from SelectQuery
        if "columns" in params:
            from shenas_transformers.sql.query import SelectQuery

            source_qualified = f'"{self.source_ref.schema}"."{self.source_ref.table}"'
            query = SelectQuery.from_dict(params)
            sql, bind_params = query.to_sql(source_qualified)
        else:
            sql = params.get("sql", "")
            bind_params = []

        if not sql:
            return []
        from app.database import cursor

        with cursor() as cur:
            preview_sql = f"SELECT * FROM ({sql}) AS _preview LIMIT {limit}"
            rows = cur.execute(preview_sql, bind_params).fetchall() if bind_params else cur.execute(preview_sql).fetchall()
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
                # Update the step too
                steps = TransformStep.for_transform(transform.id)
                if steps:
                    steps[0].params = params_json
                    steps[0].save()
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
            result = _execute_pipeline(transform, plugin_cache, device_id)
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
            result = _execute_pipeline(transform, plugin_cache, device_id)
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


# ---------------------------------------------------------------------------
# Pipeline execution
# ---------------------------------------------------------------------------


def _execute_pipeline(
    transform: Transform,
    plugin_cache: dict[str, Any],
    device_id: str,
) -> int:
    """Execute all steps in a transform pipeline.

    Single-step pipelines pass source/target straight through.
    Multi-step pipelines chain via DuckDB temp tables.
    """
    steps = transform.steps
    if not steps:
        return 0

    # Single-step: no temp tables, direct pass-through
    if len(steps) == 1:
        plugin = _get_transform_plugin(steps[0].transformer, plugin_cache)
        if plugin is None:
            log.warning("No transformer plugin for type=%s, skipping #%d", steps[0].transformer, transform.id)
            return 0
        step_view = _StepView(transform, steps[0], transform.source_ref, transform.target_ref)
        return plugin.execute(step_view, device_id=device_id)

    return _execute_multi_step(transform, steps, plugin_cache, device_id)


def _execute_multi_step(
    transform: Transform,
    steps: list[TransformStep],
    plugin_cache: dict[str, Any],
    device_id: str,
) -> int:
    """Chain multiple steps via DuckDB temp tables.

    step 0: reads pipeline source  -> writes to temp table
    step N: reads prev temp table  -> writes to pipeline target
    """
    from app.database import cursor

    temp_tables: list[str] = []
    try:
        for index, step in enumerate(steps):
            plugin = _get_transform_plugin(step.transformer, plugin_cache)
            if plugin is None:
                log.warning(
                    "No transformer plugin for type=%s, skipping transform #%d step #%d",
                    step.transformer,
                    transform.id,
                    step.ordinal,
                )
                return 0

            step_source = transform.source_ref if index == 0 else DataResourceRef(schema="temp", table=temp_tables[-1])
            step_target = _create_step_target(transform, step, index, len(steps), step_source, temp_tables)

            step_view = _StepView(transform, step, step_source, step_target)
            result = plugin.execute(step_view, device_id=device_id)
            if not result:
                return 0

        return 1
    finally:
        if temp_tables:
            with cursor() as con:
                for temp_name in temp_tables:
                    con.execute(f'DROP TABLE IF EXISTS temp."{temp_name}"')


def _create_step_target(
    transform: Transform,
    step: TransformStep,
    index: int,
    total: int,
    step_source: DataResourceRef,
    temp_tables: list[str],
) -> DataResourceRef:
    """Return the target ref for a step, creating a temp table for intermediate steps."""
    if index == total - 1:
        return transform.target_ref

    from app.database import cursor

    temp_name = f"_transform_{transform.id}_step_{step.ordinal}"
    temp_tables.append(temp_name)
    source_qualified = f'"{step_source.schema}"."{step_source.table}"'
    with cursor() as con:
        con.execute(f'CREATE OR REPLACE TEMP TABLE "{temp_name}" AS SELECT * FROM {source_qualified} LIMIT 0')
    return DataResourceRef(schema="temp", table=temp_name)


class _StepView:
    """Lightweight proxy that makes a TransformStep look like a Transform.

    Transformer plugins call ``transform.get_params()``,
    ``transform.source_ref``, ``transform.target_ref``, etc. This proxy
    delegates those to the step's params while providing step-specific
    source/target refs for pipeline chaining.
    """

    def __init__(
        self,
        transform: Transform,
        step: TransformStep,
        source_ref: DataResourceRef,
        target_ref: DataResourceRef,
    ) -> None:
        self._transform = transform
        self._step = step
        self._source_ref = source_ref
        self._target_ref = target_ref

    @property
    def id(self) -> int:
        return self._transform.id

    @property
    def source_ref(self) -> DataResourceRef:
        return self._source_ref

    @property
    def target_ref(self) -> DataResourceRef:
        return self._target_ref

    @property
    def source_plugin(self) -> str:
        return self._transform.source_plugin

    @property
    def source_data_resource_id(self) -> str:
        return self._source_ref.id

    @property
    def target_data_resource_id(self) -> str:
        return self._target_ref.id

    @property
    def transform_type(self) -> str:
        return self._step.transformer

    @property
    def params(self) -> str:
        return self._step.params

    def get_params(self) -> dict[str, Any]:
        return self._step.get_params()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
