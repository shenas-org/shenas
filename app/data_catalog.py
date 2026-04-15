"""Unified data catalog: runtime-derived metadata + persistent annotations.

The catalog walks installed plugins (sources and datasets) to derive
table metadata from code, then enriches each resource with user annotations
(freshness tracking, quality expectations, notes, tags) from the
``resource_annotations`` table.

"""

from __future__ import annotations

import contextlib
import importlib
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Any

from app.catalog import DataResourceRef
from app.plugin import Plugin
from app.table import Field, Table

if TYPE_CHECKING:
    from shenas_transformers.core.transform import Transform

log = logging.getLogger(f"shenas.{__name__}")

# ---------------------------------------------------------------------------
# Helper dataclasses (not Table subclasses -- pure value objects)
# ---------------------------------------------------------------------------


@dataclass
class ColumnMeta:
    name: str
    db_type: str
    nullable: bool
    description: str
    unit: str | None = None
    value_range: list[float] | None = None
    example_value: str | None = None
    interpretation: str | None = None


@dataclass
class TimeMeta:
    time_at: str | None = None
    time_start: str | None = None
    time_end: str | None = None
    cursor_column: str | None = None
    observed_at_injected: bool = False


@dataclass
class QualityCheck:
    check_type: str
    status: str
    message: str = ""
    value: str | None = None
    checked_at: str = ""


@dataclass
class DataResource:
    """Full representation of a data resource: code metadata + annotations."""

    ref: DataResourceRef
    display_name: str
    description: str
    plugin: Plugin
    kind: str | None = None
    query_hint: str | None = None
    as_of_macro: str | None = None
    primary_key: list[str] = field(default_factory=list)
    columns: list[ColumnMeta] = field(default_factory=list)
    time_columns: TimeMeta = field(default_factory=TimeMeta)

    # Annotation layer
    last_refreshed: str | None = None
    freshness_sla_minutes: int | None = None
    expected_row_count_min: int | None = None
    expected_row_count_max: int | None = None
    actual_row_count: int | None = None
    user_notes: str = ""
    tags: list[str] = field(default_factory=list)
    description_override: str | None = None

    # Quality
    quality_checks: list[QualityCheck] = field(default_factory=list)

    # Lineage (populated on detail view) -- transforms feeding into / out of this resource
    upstream_transforms: list[Transform] | None = None
    downstream_transforms: list[Transform] | None = None

    @property
    def id(self) -> str:
        return self.ref.id

    @property
    def effective_description(self) -> str:
        return self.description_override or self.description

    @property
    def is_stale(self) -> bool:
        if not self.freshness_sla_minutes or not self.last_refreshed:
            return False
        try:
            refreshed = datetime.fromisoformat(self.last_refreshed)
            return (datetime.now(UTC) - refreshed).total_seconds() > self.freshness_sla_minutes * 60
        except (ValueError, TypeError):
            return False

    @classmethod
    def from_table_metadata(cls, meta: dict, *, plugin: Plugin) -> DataResource:
        ref = DataResourceRef(
            schema=meta.get("schema") or "metrics",
            table=meta["table"],
        )
        time_raw = meta.get("time_columns", {})
        return cls(
            ref=ref,
            display_name=meta.get("display_name", meta["table"]),
            description=meta.get("description") or "",
            plugin=plugin,
            kind=meta.get("kind"),
            query_hint=meta.get("query_hint"),
            as_of_macro=meta.get("as_of_macro"),
            primary_key=meta.get("primary_key", []),
            columns=[
                ColumnMeta(
                    name=c["name"],
                    db_type=c.get("db_type", ""),
                    nullable=c.get("nullable", True),
                    description=c.get("description", ""),
                    unit=c.get("unit"),
                    value_range=c.get("value_range"),
                    example_value=str(c["example_value"]) if c.get("example_value") is not None else None,
                    interpretation=c.get("interpretation"),
                )
                for c in meta.get("columns", [])
            ],
            time_columns=TimeMeta(
                time_at=time_raw.get("time_at"),
                time_start=time_raw.get("time_start"),
                time_end=time_raw.get("time_end"),
                cursor_column=time_raw.get("cursor_column"),
                observed_at_injected=time_raw.get("observed_at_injected", False),
            ),
        )


# ---------------------------------------------------------------------------
# Annotation tables (DuckDB persistence)
# ---------------------------------------------------------------------------


@dataclass
class ResourceAnnotation(Table):
    class _Meta:
        name = "resource_annotations"
        display_name = "Resource Annotations"
        description = "User annotations and freshness tracking for data resources."
        schema = "shenas_system"
        pk = ("data_resource_id",)

    data_resource_id: Annotated[str, Field(db_type="VARCHAR", description="DataResource ID (schema.table)")]
    last_refreshed: Annotated[str | None, Field(db_type="TIMESTAMP", description="When last refreshed by sync/transform")] = (
        None
    )
    freshness_sla_minutes: Annotated[int | None, Field(db_type="INTEGER", description="Max acceptable staleness")] = None
    expected_row_count_min: Annotated[int | None, Field(db_type="INTEGER", description="Min expected row count")] = None
    expected_row_count_max: Annotated[int | None, Field(db_type="INTEGER", description="Max expected row count")] = None
    user_notes: Annotated[str, Field(db_type="VARCHAR", description="User notes (markdown)", db_default="''")] = ""
    tags: Annotated[str, Field(db_type="VARCHAR", description="Comma-separated tags", db_default="''")] = ""
    description_override: Annotated[str | None, Field(db_type="VARCHAR", description="User description override")] = None


@dataclass
class QualityCheckResult(Table):
    class _Meta:
        name = "quality_check_results"
        display_name = "Quality Check Results"
        description = "Results of data quality checks."
        schema = "shenas_system"
        pk = ("data_resource_id", "check_type", "checked_at")

    data_resource_id: Annotated[str, Field(db_type="VARCHAR", description="DataResource ID")]
    check_type: Annotated[str, Field(db_type="VARCHAR", description="Check type")]
    status: Annotated[str, Field(db_type="VARCHAR", description="pass/warn/fail", db_default="''")] = ""
    message: Annotated[str, Field(db_type="VARCHAR", description="Result message", db_default="''")] = ""
    value: Annotated[str | None, Field(db_type="VARCHAR", description="Actual value")] = None
    checked_at: Annotated[str, Field(db_type="TIMESTAMP", description="When checked", db_default="current_timestamp")] = ""


# DQV (W3C Data Quality Vocabulary) standard dimensions. These are the
# canonical quality axes used across data catalogs and are open-ended --
# plugins can emit their own dimension slugs too. Exposed as a constant
# so UI / dashboards can map dimension -> icon / display name without
# each consumer re-inventing the list.
DQV_DIMENSIONS: dict[str, str] = {
    "completeness": "Fraction of expected fields / rows that are populated.",
    "timeliness": "How soon data is available after the observed event.",
    "freshness": "Age of the most recent row vs now.",
    "availability": "Fraction of sync attempts that succeed.",
    "accuracy": "Agreement between recorded and ground-truth values.",
    "consistency": "Agreement across tables that describe the same entity.",
    "conformance": "Fraction of rows that pass declared schema constraints.",
}


@dataclass
class QualityMeasurement(Table):
    """Numeric quality observation for a data resource, per DQV.

    DQV (W3C Data Quality Vocabulary) models quality as a time series of
    :class:`dqv:QualityMeasurement` values along named dimensions
    (completeness, timeliness, freshness, availability, ...). Distinct from
    :class:`QualityCheckResult`, which is a pass/warn/fail gate: a
    measurement is just an observed number, and the caller decides whether
    the number is acceptable.
    """

    class _Meta:
        name = "quality_measurements"
        display_name = "Quality Measurements"
        description = "Time-series of DQV-style numeric quality observations."
        schema = "shenas_system"
        pk = ("data_resource_id", "dimension", "measured_at")

    data_resource_id: Annotated[str, Field(db_type="VARCHAR", description="DataResource ID (schema.table)")]
    dimension: Annotated[
        str,
        Field(
            db_type="VARCHAR",
            description="DQV dimension slug (completeness, timeliness, freshness, availability, ...).",
        ),
    ]
    value: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Numeric measurement value; unit is dimension-specific."),
    ] = None
    unit: Annotated[
        str,
        Field(db_type="VARCHAR", description="SI / SI-derived unit (percent, s, min, bytes, count).", db_default="''"),
    ] = ""
    measured_at: Annotated[
        str,
        Field(db_type="TIMESTAMP", description="When the measurement was taken.", db_default="current_timestamp"),
    ] = ""
    computed_by: Annotated[
        str,
        Field(
            db_type="VARCHAR",
            description="What computed this value (sync / transform / manual).",
            db_default="''",
        ),
    ] = ""
    note: Annotated[str, Field(db_type="VARCHAR", description="Optional free-text note.", db_default="''")] = ""


# ---------------------------------------------------------------------------
# Catalog walk logic
# ---------------------------------------------------------------------------


def _walk_sources() -> list[tuple[dict, Plugin]]:
    """Return [(table_metadata, plugin_instance)] for source tables."""
    out: list[tuple[dict, Plugin]] = []
    for src_cls in Plugin.load_by_kind("source", include_internal=False):
        try:
            tables_mod = importlib.import_module(f"shenas_sources.{src_cls.name}.tables")
        except ImportError:
            continue
        plugin = src_cls()
        out.extend((t.table_metadata(), plugin) for t in getattr(tables_mod, "TABLES", ()))
    return out


def _walk_metrics() -> list[tuple[dict, Plugin]]:
    """Return [(table_metadata, plugin_instance)] for metric tables."""
    from app.plugin import PluginInstance
    from shenas_datasets.core import Dataset

    out: list[tuple[dict, Plugin]] = []
    for dataset_cls in Dataset.load_all(include_internal=False):
        plugin = dataset_cls()
        out.extend((t.table_metadata(), plugin) for t in getattr(dataset_cls, "all_tables", ()))
    where = (
        "kind = 'dataset'"
        " AND (is_suggested IS NULL OR is_suggested = FALSE)"
        " AND metadata_json IS NOT NULL AND metadata_json != ''"
    )
    for pi in PluginInstance.all(where=where, order_by="name"):
        # Data-defined datasets don't have a plugin class -- create a stub
        stub = Plugin.__new__(Plugin)
        stub.name = pi.name
        stub.display_name = pi.name
        stub._kind = "dataset"
        out.extend((meta, stub) for meta in Dataset.suggested_metadata(pi))
    return out


# ---------------------------------------------------------------------------
# DataCatalog
# ---------------------------------------------------------------------------


class DataCatalog:
    """Unified entry point for all catalog operations."""

    _resource_cache: dict[str, DataResource] | None = None

    def get_resource(self, resource_id: str) -> DataResource:
        """Look up a single DataResource by ID. Cached, no lineage.

        Returns a stub for unknown resources (e.g. tables that exist in
        DuckDB but aren't part of any installed plugin).
        """
        if self._resource_cache is None:
            self._resource_cache = {r.id: r for r in self._walk_all()}
        if resource_id in self._resource_cache:
            return self._resource_cache[resource_id]
        ref = DataResourceRef.from_id(resource_id)
        stub_plugin = Plugin.__new__(Plugin)
        stub_plugin.name = ref.schema
        stub_plugin.display_name = ref.schema
        return DataResource(
            ref=ref,
            display_name=ref.table,
            description="",
            plugin=stub_plugin,
        )

    def _walk_all(self) -> list[DataResource]:
        """Build DataResource list from code-derived metadata."""
        resources: list[DataResource] = []
        for meta, plugin in _walk_sources():
            resources.append(DataResource.from_table_metadata(meta, plugin=plugin))
        for meta, plugin in _walk_metrics():
            resources.append(DataResource.from_table_metadata(meta, plugin=plugin))
        return resources

    def _enrich_with_annotations(self, resources: list[DataResource]) -> None:
        """Merge annotations from DuckDB into the resource list."""
        try:
            annotations = {a.data_resource_id: a for a in ResourceAnnotation.all()}
        except Exception:
            return
        for r in resources:
            ann = annotations.get(r.id)
            if ann:
                r.last_refreshed = ann.last_refreshed
                r.freshness_sla_minutes = ann.freshness_sla_minutes
                r.expected_row_count_min = ann.expected_row_count_min
                r.expected_row_count_max = ann.expected_row_count_max
                r.user_notes = ann.user_notes or ""
                r.tags = [t.strip() for t in (ann.tags or "").split(",") if t.strip()]
                r.description_override = ann.description_override

    def _enrich_with_row_counts(self, resources: list[DataResource]) -> None:
        """Add live row counts from DuckDB."""
        from app.database import cursor

        for r in resources:
            try:
                with cursor() as cur:
                    row = cur.execute(f'SELECT COUNT(*) FROM "{r.ref.schema}"."{r.ref.table}"').fetchone()
                    r.actual_row_count = row[0] if row else None
            except Exception:
                pass

    def list_resources(
        self,
        *,
        kind: str | None = None,
        plugin: str | None = None,
        tags: str | None = None,
        stale_only: bool = False,
        include_row_counts: bool = True,
    ) -> list[DataResource]:
        resources = self._walk_all()
        self._enrich_with_annotations(resources)
        if include_row_counts:
            self._enrich_with_row_counts(resources)

        if kind:
            resources = [r for r in resources if r.kind == kind]
        if plugin:
            resources = [r for r in resources if r.plugin.name == plugin]
        if tags:
            tag_set = {t.strip().lower() for t in tags.split(",")}
            resources = [r for r in resources if tag_set & {t.lower() for t in r.tags}]
        if stale_only:
            resources = [r for r in resources if r.is_stale]

        return sorted(resources, key=lambda r: r.id)

    def get(self, data_resource_id: str) -> DataResource | None:
        """Single resource with quality checks and lineage."""
        resources = self._walk_all()
        self._enrich_with_annotations(resources)
        resource = next((r for r in resources if r.id == data_resource_id), None)
        if not resource:
            return None
        # Row count
        self._enrich_with_row_counts([resource])
        # Quality checks
        try:
            checks = QualityCheckResult.all(
                where="data_resource_id = ?",
                params=[data_resource_id],
                order_by="checked_at DESC",
            )
            resource.quality_checks = [
                QualityCheck(
                    check_type=c.check_type,
                    status=c.status,
                    message=c.message,
                    value=c.value,
                    checked_at=c.checked_at,
                )
                for c in checks[:10]
            ]
        except Exception:
            pass
        # Lineage -- transforms feeding into / out of this resource
        lineage = self._lineage_transforms(data_resource_id)
        resource.upstream_transforms = lineage["upstream"]
        resource.downstream_transforms = lineage["downstream"]
        return resource

    def metadata_by_id(self) -> dict[str, dict[str, Any]]:
        """Return {data_resource_id: table_metadata_dict}."""
        out: dict[str, dict[str, Any]] = {}
        for meta, _name in _walk_sources() + _walk_metrics():
            schema = meta.get("schema") or "metrics"
            key = f"{schema}.{meta['table']}"
            out[key] = meta
        return out

    def _lineage_transforms(self, data_resource_id: str) -> dict[str, list[Transform]]:
        """Transforms feeding into (upstream) / out of (downstream) this resource."""
        from shenas_transformers.core.transform import Transform

        upstream: list[Transform] = []
        downstream: list[Transform] = []
        try:
            for t in Transform.all():
                if not t.enabled:
                    continue
                if t.target_ref.id == data_resource_id:
                    upstream.append(t)
                if t.source_ref.id == data_resource_id:
                    downstream.append(t)
        except Exception:
            pass
        return {"upstream": upstream, "downstream": downstream}

    def mark_refreshed(self, schema: str, table: str | None = None) -> None:
        """Upsert last_refreshed = now() for one table or all in a schema."""
        now = datetime.now(UTC).isoformat()
        if table:
            self._upsert_annotation(f"{schema}.{table}", last_refreshed=now)
        else:
            resources = self._walk_all()
            for r in resources:
                if r.ref.schema == schema:
                    self._upsert_annotation(r.id, last_refreshed=now)

    def annotate(self, data_resource_id: str, **fields: Any) -> DataResource | None:
        """Update user-editable fields. Creates annotation row if missing."""
        self._upsert_annotation(data_resource_id, **fields)
        return self.get(data_resource_id)

    def run_quality_checks(self, data_resource_id: str | None = None) -> list[QualityCheck]:
        """Run checks and store results."""
        resources = self._walk_all()
        self._enrich_with_annotations(resources)
        if data_resource_id:
            resources = [r for r in resources if r.id == data_resource_id]

        results: list[QualityCheck] = []
        now = datetime.now(UTC).isoformat()
        from app.database import cursor

        for r in resources:
            # Row count check
            if r.expected_row_count_min is not None or r.expected_row_count_max is not None:
                try:
                    with cursor() as cur:
                        row = cur.execute(f'SELECT COUNT(*) FROM "{r.ref.schema}"."{r.ref.table}"').fetchone()
                        count = row[0] if row else 0
                except Exception:
                    count = 0
                status = "pass"
                msg = f"{count} rows"
                if r.expected_row_count_min is not None and count < r.expected_row_count_min:
                    status = "fail"
                    msg = f"{count} rows < min {r.expected_row_count_min}"
                if r.expected_row_count_max is not None and count > r.expected_row_count_max:
                    status = "warn"
                    msg = f"{count} rows > max {r.expected_row_count_max}"
                check = QualityCheck(check_type="row_count", status=status, message=msg, value=str(count), checked_at=now)
                results.append(check)
                self._store_check(r.id, check)

            # Freshness check
            if r.freshness_sla_minutes and r.last_refreshed:
                status = "fail" if r.is_stale else "pass"
                msg = f"last refreshed {r.last_refreshed}"
                check = QualityCheck(check_type="freshness", status=status, message=msg, checked_at=now)
                results.append(check)
                self._store_check(r.id, check)

        return results

    def _upsert_annotation(self, data_resource_id: str, **fields: Any) -> None:

        existing = ResourceAnnotation.find(data_resource_id)
        if existing:
            for k, v in fields.items():
                if v is not None:
                    setattr(existing, k, v)
            existing.save()
        else:
            ann = ResourceAnnotation(data_resource_id=data_resource_id, **fields)
            ann.insert()

    def _store_check(self, data_resource_id: str, check: QualityCheck) -> None:
        result = QualityCheckResult(
            data_resource_id=data_resource_id,
            check_type=check.check_type,
            status=check.status,
            message=check.message,
            value=check.value,
            checked_at=check.checked_at,
        )
        with contextlib.suppress(Exception):
            result.insert()


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

_catalog: DataCatalog | None = None


def catalog() -> DataCatalog:
    global _catalog
    if _catalog is None:
        _catalog = DataCatalog()
    return _catalog
